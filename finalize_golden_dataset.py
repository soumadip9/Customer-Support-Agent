import csv
import json
import os
import sys

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

def finalize():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(base_dir, 'golden_review.csv')
    output_jsonl_path = os.path.join(base_dir, 'golden_dataset.jsonl')
    
    print(f"Reading human review file: {csv_path}")
    
    if not os.path.exists(csv_path):
        print(f"ERROR: {csv_path} does not exist.")
        sys.exit(1)
        
    rows = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for line_num, row in enumerate(reader, 2):
            rows.append((line_num, row))
            
    total_rows = len(rows)
    print(f"Total review rows loaded: {total_rows}")
    
    if total_rows == 0:
        print("ERROR: Review CSV is empty.")
        sys.exit(1)
        
    seen_tweet_ids = set()
    errors = []
    final_records = []
    
    for line_num, row in rows:
        rev_id = row.get('review_id', f"rev_{len(final_records)+1:03d}")
        tweet_id = str(row.get('source_tweet_id', '')).strip()
        msg = row.get('customer_message', '').strip()
        
        h_intent = row.get('human_intent', '').strip()
        h_decision = row.get('human_escalation_decision', '').strip()
        h_reason = row.get('human_escalation_reason', '').strip()
        
        # 1. Check tweet ID
        if not tweet_id:
            errors.append(f"Line {line_num} ({rev_id}): Missing source_tweet_id.")
        elif tweet_id in seen_tweet_ids:
            errors.append(f"Line {line_num} ({rev_id}): Duplicate source_tweet_id '{tweet_id}'.")
        seen_tweet_ids.add(tweet_id)
        
        # 2. Check message
        if not msg:
            errors.append(f"Line {line_num} ({rev_id}): Missing customer_message.")
            
        # 3. Check human_intent
        if not h_intent:
            errors.append(f"Line {line_num} ({rev_id}): 'human_intent' is empty. Human review has not been completed.")
        elif h_intent not in VALID_INTENTS:
            errors.append(f"Line {line_num} ({rev_id}): Invalid human_intent '{h_intent}'. Must be one of {sorted(list(VALID_INTENTS))}.")
            
        # 4. Check human_escalation_decision
        if not h_decision:
            errors.append(f"Line {line_num} ({rev_id}): 'human_escalation_decision' is empty.")
        elif h_decision not in VALID_DECISIONS:
            errors.append(f"Line {line_num} ({rev_id}): Invalid human_escalation_decision '{h_decision}'. Must be 'AUTO_HANDLE' or 'ESCALATE'.")
            
        # 5. Check human_escalation_reason
        if h_decision == 'ESCALATE' and not h_reason:
            errors.append(f"Line {line_num} ({rev_id}): Missing 'human_escalation_reason' for ESCALATE decision.")
            
        final_records.append({
            'id': f"golden_{len(final_records)+1:03d}",
            'customer_message': msg,
            'intent': h_intent,
            'escalation_decision': h_decision,
            'escalation_reason': h_reason if h_decision == 'ESCALATE' else (h_reason or "Safe for automated handling."),
            'source_tweet_id': tweet_id
        })
        
    if errors:
        print("\n" + "="*50)
        print(f"VALIDATION FAILED: {len(errors)} error(s) found in human review file:")
        for err in errors[:15]:
            print(f"  - {err}")
        if len(errors) > 15:
            print(f"  ... and {len(errors) - 15} more errors.")
        print("="*50)
        print("\nPlease complete the human review in 'golden_review.csv' and re-run this script.")
        sys.exit(1)
        
    # Write final golden_dataset.jsonl from human annotations
    with open(output_jsonl_path, 'w', encoding='utf-8') as f:
        for rec in final_records:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
            
    print(f"\nSUCCESS: Successfully finalized {len(final_records)} human-reviewed records to {output_jsonl_path}!")
    sys.exit(0)

if __name__ == '__main__':
    finalize()
