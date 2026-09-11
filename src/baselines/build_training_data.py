"""
build_training_data.py

Scans the TWCS dataset for AmazonHelp inbound customer messages,
applies deterministic intent patterns, and writes:
  data/training_data.jsonl   — all labeled training examples

Excludes the 200 golden evaluation tweet IDs from training data.
Uses a fixed random seed for reproducibility.
"""
import zipfile
import csv
import io
import json
import random
import re
import os
from collections import defaultdict

SEED = 42
random.seed(SEED)

ZIP_PATH = r"c:\CustomerSupport\archive (4).zip"
TWCS_CSV = "twcs/twcs.csv"
GOLDEN_JSONL = r"c:\CustomerSupport\golden_dataset.jsonl"
OUTPUT_PATH = r"c:\CustomerSupport\data\training_data.jsonl"

VALID_INTENTS = [
    "delivery_delay", "order_tracking_inquiry", "order_cancellation",
    "refund_inquiry", "damaged_or_wrong_item", "payment_and_billing_issue",
    "prime_membership_inquiry", "account_access_and_security",
    "driver_and_packaging_feedback", "general_product_and_service_faq",
    "digital_and_device_troubleshooting", "promotion_and_discount_inquiry",
    "other_or_unsupported",
]

# Default escalation policy per intent (from taxonomy)
ESCALATION_POLICY = {
    "delivery_delay": "ESCALATE",
    "order_tracking_inquiry": "AUTO_HANDLE",
    "order_cancellation": "ESCALATE",
    "refund_inquiry": "ESCALATE",
    "damaged_or_wrong_item": "ESCALATE",
    "payment_and_billing_issue": "ESCALATE",
    "prime_membership_inquiry": "AUTO_HANDLE",
    "account_access_and_security": "ESCALATE",
    "driver_and_packaging_feedback": "AUTO_HANDLE",
    "general_product_and_service_faq": "AUTO_HANDLE",
    "digital_and_device_troubleshooting": "AUTO_HANDLE",
    "promotion_and_discount_inquiry": "AUTO_HANDLE",
    "other_or_unsupported": "ESCALATE",
}

# High-precision intent patterns (same as candidate pool builder)
PATTERNS = {
    "delivery_delay": [
        r"\b(late|overdue|delayed|hasn'?t arrived|not arrived|still waiting|supposed to be delivered|supposed to arrive|never arrived|where is my package|where is my delivery|where is my order|running late|past delivery date|hasn't shown up|missed delivery)\b"
    ],
    "order_tracking_inquiry": [
        r"\b(tracking number|how do i track|can you track|carrier|courier|dispatch status|when will it ship|when will it be dispatched|estimated delivery date|track my parcel|live tracking)\b"
    ],
    "order_cancellation": [
        r"\b(cancel my order|cancelled my order|cancelling my order|how to cancel|unable to cancel|cancel order|stop shipment|order was cancelled|why was my order cancelled|reinstate my order)\b"
    ],
    "refund_inquiry": [
        r"\b(refund|money back|return credit|when will i get my refund|refund not processed|waiting for refund|refund status|return postage refund|get my money)\b"
    ],
    "damaged_or_wrong_item": [
        r"\b(damaged|broken|smashed|crushed|opened|tampered|missing items?|wrong item|wrong size|wrong product|defective|faulty|shattered|bent|cracked|incomplete order)\b"
    ],
    "payment_and_billing_issue": [
        r"\b(charged twice|double charged?|money deducted|unauthorized charge|payment failed|card declined|gift card balance|billing issue|charged extra|debited twice|duplicate charge|money taken)\b"
    ],
    "prime_membership_inquiry": [
        r"\b(prime membership|prime member|pay prime|cancel prime|prime renewal|prime household|prime student|share prime|prime benefits|prime video catalog|prime subscription)\b"
    ],
    "account_access_and_security": [
        r"\b(account locked|can'?t log ?in|2step|two-factor|otp|password reset|close my account|account hacked|unauthorized login|verification code|sign in error|lost access|account compromised)\b"
    ],
    "driver_and_packaging_feedback": [
        r"\b(delivery driver|courier driver|driver threw|left in rain|packaging was|terrible packaging|excessive packaging|driver blocked|left on porch|package box|driver left|delivery man)\b"
    ],
    "general_product_and_service_faq": [
        r"\b(is it in stock|when will you restock|trade.?in|warranty on|refurbished warranty|holiday return window|international shipping|is this authentic|pre.?order|return policy|trade in eligible)\b"
    ],
    "digital_and_device_troubleshooting": [
        r"\b(kindle|echo dot|alexa|firestick|fire tv|prime video app|app error|error code|frozen screen|audible app|app crashes|unresponsive|fire tablet|amazon music app|echo show)\b"
    ],
    "promotion_and_discount_inquiry": [
        r"\b(promo code|promotional code|coupon code|discount voucher|black friday|cyber monday|price match|student voucher|promotional discount|deal expired|coupon not working)\b"
    ],
}

# Caps per intent to avoid severe imbalance in training data
INTENT_CAP = 3000
OTHER_CAP = 2000

def classify_message(text):
    """Return single intent label or None if multi-match/no-match."""
    t_lower = text.lower()
    matches = []
    for intent, pat_list in PATTERNS.items():
        for p in pat_list:
            if re.search(p, t_lower):
                matches.append(intent)
                break
    if len(matches) == 1:
        return matches[0]
    return None  # multi or no match → candidate for other_or_unsupported

def is_english(text):
    """Rough English filter: reject high-Unicode non-ASCII content."""
    non_ascii = sum(1 for c in text if ord(c) > 0x00FF)
    return non_ascii / max(len(text), 1) < 0.15

def is_noisy(text):
    """True if message is too short or clearly not a support ticket."""
    words = text.split()
    if len(words) < 5:
        return True
    return False


def main():
    # Load golden tweet IDs to exclude
    golden_tids = set()
    with open(GOLDEN_JSONL, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                golden_tids.add(str(rec['source_tweet_id']))
    print(f"Loaded {len(golden_tids)} golden tweet IDs to exclude from training.")

    intent_pools = defaultdict(list)
    other_pool = []
    seen_tids = set()
    seen_texts = set()
    scanned = 0

    print("Scanning TWCS for AmazonHelp inbound messages...")
    with zipfile.ZipFile(ZIP_PATH, 'r') as z:
        with z.open(TWCS_CSV) as f:
            text_stream = io.TextIOWrapper(f, encoding='utf-8', errors='replace')
            reader = csv.reader(text_stream)
            next(reader)  # skip header
            for row in reader:
                if not row or len(row) < 7:
                    continue
                tid, author_id, inbound, created_at, text = row[0], row[1], row[2], row[3], row[4]
                scanned += 1

                if inbound.strip().lower() != 'true':
                    continue
                if '@amazonhelp' not in text.lower():
                    continue
                if tid in golden_tids or tid in seen_tids:
                    continue

                t_clean = ' '.join(text.split())
                if t_clean in seen_texts:
                    continue

                seen_tids.add(tid)
                seen_texts.add(t_clean)

                # Check caps to avoid scanning entire 516MB unnecessarily
                all_capped = all(len(v) >= INTENT_CAP for v in intent_pools.values())
                if all_capped and len(other_pool) >= OTHER_CAP:
                    break

                intent = classify_message(text)

                if intent and len(intent_pools[intent]) < INTENT_CAP:
                    if is_english(text) and not is_noisy(text):
                        intent_pools[intent].append({'tweet_id': tid, 'text': text, 'intent': intent})
                elif intent is None and len(other_pool) < OTHER_CAP:
                    if is_english(text) and not is_noisy(text):
                        other_pool.append({'tweet_id': tid, 'text': text, 'intent': 'other_or_unsupported'})

    print(f"Scanned {scanned:,} rows total.")
    print("\nRaw intent pool sizes:")
    for intent in VALID_INTENTS[:-1]:
        print(f"  {intent}: {len(intent_pools.get(intent, [])): >5}")
    print(f"  other_or_unsupported: {len(other_pool): >5}")

    # Assemble final training records
    all_records = []
    for intent in VALID_INTENTS[:-1]:
        pool = intent_pools.get(intent, [])
        random.shuffle(pool)
        for item in pool:
            all_records.append({
                'tweet_id': item['tweet_id'],
                'customer_message': item['text'],
                'intent': item['intent'],
                'escalation_decision': ESCALATION_POLICY[item['intent']],
            })

    # Add other_or_unsupported sample
    random.shuffle(other_pool)
    for item in other_pool[:OTHER_CAP]:
        all_records.append({
            'tweet_id': item['tweet_id'],
            'customer_message': item['text'],
            'intent': 'other_or_unsupported',
            'escalation_decision': 'ESCALATE',
        })

    # Shuffle all records together
    random.shuffle(all_records)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        for rec in all_records:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')

    print(f"\nWrote {len(all_records):,} training records to {OUTPUT_PATH}")

    # Summary stats
    from collections import Counter
    intent_counts = Counter(r['intent'] for r in all_records)
    esc_counts = Counter(r['escalation_decision'] for r in all_records)
    print("\nFinal training intent distribution:")
    for intent, cnt in intent_counts.most_common():
        print(f"  {intent}: {cnt}")
    print("\nEscalation distribution:")
    for dec, cnt in esc_counts.most_common():
        print(f"  {dec}: {cnt}")

if __name__ == '__main__':
    main()
