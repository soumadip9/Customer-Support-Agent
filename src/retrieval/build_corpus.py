"""
src/retrieval/build_corpus.py

Extracts high-quality historical customer message -> AmazonHelp response pairs
from the TWCS dataset (archive (4).zip / twcs.csv).

Rules:
  1. Exclude all 200 golden evaluation tweet IDs.
  2. Require genuine inbound customer message mentioning @AmazonHelp.
  3. Match with the direct AmazonHelp reply tweet.
  4. Filter out non-English and very short noisy messages.
  5. Save to data/retrieval_corpus.jsonl.
"""

import csv
import io
import json
import os
import random
import zipfile

SEED = 42
random.seed(SEED)

ZIP_PATH = r"c:\CustomerSupport\archive (4).zip"
TWCS_CSV = "twcs/twcs.csv"
GOLDEN_PATH = r"c:\CustomerSupport\golden_dataset.jsonl"
OUTPUT_CORPUS = r"c:\CustomerSupport\data\retrieval_corpus.jsonl"
CORPUS_TARGET_SIZE = 15000  # High quality, compact, fast to embed


def is_english(text: str) -> bool:
    """Rough English check: reject messages with high non-ASCII content."""
    non_ascii = sum(1 for c in text if ord(c) > 0x00FF)
    return (non_ascii / max(len(text), 1)) < 0.15


def is_valid_message(text: str) -> bool:
    words = text.split()
    return len(words) >= 4


def extract_retrieval_corpus(
    zip_path: str = ZIP_PATH,
    golden_path: str = GOLDEN_PATH,
    output_path: str = OUTPUT_CORPUS,
    target_size: int = CORPUS_TARGET_SIZE,
) -> int:
    # 1. Load golden tweet IDs to strictly exclude
    golden_tids = set()
    if os.path.exists(golden_path):
        with open(golden_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line.strip())
                    golden_tids.add(str(rec["source_tweet_id"]))
    print(f"Excluding {len(golden_tids)} golden tweet IDs from retrieval corpus.")

    # 2. First pass: Collect all AmazonHelp outbound responses (tweet_id -> text)
    #    and candidate inbound customer tweets
    print("Streaming TWCS dataset from zip archive...")
    
    amazon_responses = {}  # response_tweet_id -> reply_text
    inbound_candidates = []  # list of (tweet_id, customer_text, response_tweet_id)
    
    with zipfile.ZipFile(zip_path, "r") as z:
        with z.open(TWCS_CSV) as f:
            text_stream = io.TextIOWrapper(f, encoding="utf-8", errors="replace")
            reader = csv.reader(text_stream)
            header = next(reader)
            # tweet_id: 0, author_id: 1, inbound: 2, created_at: 3, text: 4, response_tweet_id: 5, in_response_to_tweet_id: 6
            
            for row in reader:
                if len(row) < 7:
                    continue
                tid, author, inbound_str, _, text, resp_ids_str, in_resp_to = row[0], row[1], row[2], row[3], row[4], row[5], row[6]
                
                # Check if this is an AmazonHelp agent response
                if author == "AmazonHelp":
                    amazon_responses[tid] = text
                
                # Check if this is an inbound customer tweet directed at AmazonHelp
                if inbound_str.strip().lower() == "true" and "@amazonhelp" in text.lower():
                    if tid not in golden_tids and is_english(text) and is_valid_message(text):
                        # Get first response tweet id if available
                        first_resp = resp_ids_str.split(",")[0].strip() if resp_ids_str else ""
                        inbound_candidates.append({
                            "tweet_id": tid,
                            "text": text,
                            "response_tweet_id": first_resp,
                        })

    print(f"Collected {len(amazon_responses):,} AmazonHelp responses.")
    print(f"Collected {len(inbound_candidates):,} eligible inbound customer candidate tweets.")

    # 3. Match candidate customer tweets with their AmazonHelp response
    corpus_records = []
    seen_texts = set()

    random.shuffle(inbound_candidates)

    for item in inbound_candidates:
        tid = item["tweet_id"]
        c_text = " ".join(item["text"].split())
        
        if c_text in seen_texts:
            continue
        seen_texts.add(c_text)
        
        resp_id = item["response_tweet_id"]
        agent_reply = amazon_responses.get(resp_id, "")
        
        corpus_records.append({
            "source_id": tid,
            "customer_message": item["text"],
            "historical_response": agent_reply,
            "response_tweet_id": resp_id,
        })
        
        if len(corpus_records) >= target_size:
            break

    print(f"Selected {len(corpus_records):,} distinct customer-support records for retrieval corpus.")

    # 4. Save to jsonl
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for rec in corpus_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"Wrote retrieval corpus to: {output_path}")
    return len(corpus_records)


if __name__ == "__main__":
    extract_retrieval_corpus()
