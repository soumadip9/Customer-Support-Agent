import json
import os
import sys
import zipfile
import csv
import io
from collections import Counter

VALID_INTENTS = {
    'delivery_delay',
    'order_tracking_inquiry',
    'order_cancellation',
    'refund_inquiry',
    'damaged_or_wrong_item',
    'payment_and_billing_issue',
    'prime_membership_inquiry',
    'account_access_and_security',
    'driver_and_packaging_feedback',
    'general_product_and_service_faq',
    'digital_and_device_troubleshooting',
    'promotion_and_discount_inquiry',
    'other_or_unsupported'
}

VALID_DECISIONS = {'AUTO_HANDLE', 'ESCALATE'}

def validate():
    file_path = os.path.join(os.path.dirname(__file__), 'golden_dataset.jsonl')
    zip_path = os.path.join(os.path.dirname(__file__), 'archive (4).zip')
    
    print(f"Validating golden dataset: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"ERROR: File not found: {file_path}")
        sys.exit(1)
        
    records = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                records.append((line_num, rec))
            except Exception as e:
                print(f"ERROR: Invalid JSON on line {line_num}: {e}")
                sys.exit(1)
                
    total_count = len(records)
    print(f"Total records read: {total_count}")
    
    if total_count < 150 or total_count > 250:
        print(f"ERROR: Expected ~200 records, got {total_count}")
        sys.exit(1)
        
    seen_ids = set()
    seen_tweet_ids = set()
    seen_messages = set()
    intent_counts = Counter()
    decision_counts = Counter()
    
    required_fields = ['id', 'customer_message', 'intent', 'escalation_decision', 'escalation_reason', 'source_tweet_id']
    
    for line_num, rec in records:
        # Check required fields
        for field in required_fields:
            if field not in rec:
                print(f"ERROR: Missing field '{field}' on line {line_num}")
                sys.exit(1)
                
        rec_id = rec['id']
        if rec_id in seen_ids:
            print(f"ERROR: Duplicate record id '{rec_id}' on line {line_num}")
            sys.exit(1)
        seen_ids.add(rec_id)
        
        tid = str(rec['source_tweet_id']).strip()
        if not tid:
            print(f"ERROR: Empty source_tweet_id on line {line_num}")
            sys.exit(1)
        if tid in seen_tweet_ids:
            print(f"ERROR: Duplicate source_tweet_id '{tid}' on line {line_num}")
            sys.exit(1)
        seen_tweet_ids.add(tid)
        
        msg = rec['customer_message'].strip()
        if not msg:
            print(f"ERROR: Empty customer_message on line {line_num}")
            sys.exit(1)
            
        intent = rec['intent']
        if intent not in VALID_INTENTS:
            print(f"ERROR: Invalid intent '{intent}' on line {line_num}")
            sys.exit(1)
        intent_counts[intent] += 1
        
        decision = rec['escalation_decision']
        if decision not in VALID_DECISIONS:
            print(f"ERROR: Invalid escalation_decision '{decision}' on line {line_num}")
            sys.exit(1)
        decision_counts[decision] += 1
        
        reason = rec['escalation_reason'].strip()
        if decision == 'ESCALATE' and not reason:
            print(f"ERROR: Missing escalation_reason for ESCALATE decision on line {line_num}")
            sys.exit(1)

    print("\n--- Structural Verification Summary ---")
    print(f"All {total_count} records have valid fields, non-empty values, and unique IDs.")
    
    print("\n=== Intent Distribution ===")
    for intent, count in sorted(intent_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {intent:35s}: {count:3d} ({count/total_count*100:5.1f}%)")
        
    print("\n=== Escalation Distribution ===")
    for decision, count in decision_counts.items():
        print(f"  {decision:15s}: {count:3d} ({count/total_count*100:5.1f}%)")

    # Verify that all source_tweet_id actually exist in the raw dataset
    if os.path.exists(zip_path):
        print(f"\nVerifying tweet IDs against raw TWCS dataset: {zip_path}...")
        found_tids = set()
        with zipfile.ZipFile(zip_path, 'r') as z:
            with z.open('twcs/twcs.csv') as f:
                text_stream = io.TextIOWrapper(f, encoding='utf-8', errors='replace')
                reader = csv.reader(text_stream)
                next(reader)
                for row in reader:
                    if row and len(row) > 0:
                        tid = row[0]
                        if tid in seen_tweet_ids:
                            found_tids.add(tid)
                            if len(found_tids) == len(seen_tweet_ids):
                                break
                                
        missing_tids = seen_tweet_ids - found_tids
        if missing_tids:
            print(f"ERROR: {len(missing_tids)} tweet IDs not found in raw dataset: {list(missing_tids)[:5]}")
            sys.exit(1)
        print(f"SUCCESS: All {len(seen_tweet_ids)} source_tweet_id verified to exist in real dataset!")
        
    print("\n[PASSED] Golden dataset validation succeeded with 0 errors!")
    sys.exit(0)

if __name__ == '__main__':
    validate()
