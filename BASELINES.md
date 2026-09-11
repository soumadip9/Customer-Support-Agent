# Baseline Classifiers

**Project:** Hiver AI Customer Support Agent  
**Purpose:** Establish reproducible baseline performance targets that the final RAG + LLM system must outperform.

---

## 1. Dataset Used for Training

**Training data file:** `data/training_data.jsonl`  
**Source:** Real AmazonHelp inbound customer messages from the TWCS dataset (`archive (4).zip` → `twcs/twcs.csv`)

> [!IMPORTANT]
> The **200-example golden evaluation dataset** (`golden_dataset.jsonl`) is **completely excluded** from training. The 200 golden tweet IDs are explicitly filtered before any training record is written. This is verified by `tests/test_baselines.py::TestGoldenDatasetNotUsedInTraining::test_golden_ids_excluded`.

**Training set size:** **16,018 labeled examples** across 13 intent classes.

| Intent | Training Count | % of Training Set |
| :--- | :--- | :--- |
| `delivery_delay` | 3,000 | 18.7% |
| `refund_inquiry` | 3,000 | 18.7% |
| `order_tracking_inquiry` | 2,269 | 14.2% |
| `other_or_unsupported` | 2,000 | 12.5% |
| `digital_and_device_troubleshooting` | 1,590 | 9.9% |
| `damaged_or_wrong_item` | 1,503 | 9.4% |
| `prime_membership_inquiry` | 1,130 | 7.1% |
| `general_product_and_service_faq` | 472 | 2.9% |
| `promotion_and_discount_inquiry` | 304 | 1.9% |
| `order_cancellation` | 271 | 1.7% |
| `driver_and_packaging_feedback` | 210 | 1.3% |
| `account_access_and_security` | 174 | 1.1% |
| `payment_and_billing_issue` | 95 | 0.6% |
| **Total** | **16,018** | **100%** |

**Escalation distribution in training data:**

| Escalation | Count | % |
| :--- | :--- | :--- |
| `ESCALATE` | 10,043 | 62.7% |
| `AUTO_HANDLE` | 5,975 | 37.3% |

---

## 2. How Training / Validation Data Was Created

### Step 1 — Candidate Extraction
All inbound AmazonHelp customer messages were scanned from the full TWCS CSV (`2,811,774` total rows). Messages were kept if:
- `inbound == True`
- `@AmazonHelp` mentioned in the text
- Not in the golden evaluation set (200 tweet IDs excluded)
- Not a duplicate text (normalized whitespace)

### Step 2 — Deterministic Intent Labeling
Each candidate message was labeled using high-precision regular expression patterns derived from the `INTENT_TAXONOMY.md`. Only messages matching **exactly one** intent pattern were assigned that intent label (multi-match messages were discarded to keep label quality high).

### Step 3 — `other_or_unsupported` Sampling
Messages matching **no** intent pattern, passing an English language filter (≤15% non-ASCII characters) and word-count filter (≥5 words), were sampled as `other_or_unsupported` examples.

### Step 4 — Cap Applied
To prevent extreme class imbalance, high-frequency classes (`delivery_delay`, `refund_inquiry`) were capped at **3,000 examples** and `other_or_unsupported` capped at **2,000** to maintain a broadly realistic distribution.

### Step 5 — Internal Validation Split
Both TF-IDF classifiers internally split 15% of training records as a validation hold-out (stratified, reproducible). **This is separate from the golden dataset**, which is never touched during training.

```
Total training records : 16,018
  → train split        : 13,615 (85%)
  → validation split   :  2,403 (15%)
```

---

## 3. Random Seed

**Fixed seed: `42`** — applied to:
- Training/validation split (`sklearn.model_selection.train_test_split`)
- Logistic Regression initialization (`random_state=42`)
- `other_or_unsupported` candidate shuffling (`random.seed(42)`)

All results are fully reproducible.

---

## 4. Baseline 1 — Majority-Class Classifier

**File:** [`src/baselines/majority_baseline.py`](file:///c:/CustomerSupport/src/baselines/majority_baseline.py)  
**Saved model:** `models/majority_classifier.pkl`

### Methodology
The simplest possible baseline. After fitting on training data:
- **Intent prediction:** Always predicts `delivery_delay` (the most frequent training class at 18.7%).
- **Escalation prediction:** Always predicts `ESCALATE` (62.7% of training records).

No text is read, no features are computed — every input receives the same label.

### Why This Is Useful
- Sets the **floor** — any real model must beat this to be worth deploying.
- Establishes expected accuracy from a zero-skill predictor (important to confirm models don't just memorize class frequencies).
- Verifies the evaluation harness is working correctly (majority accuracy should match class distribution).

---

## 5. Baseline 2 — TF-IDF + Logistic Regression

**File:** [`src/baselines/tfidf_logreg.py`](file:///c:/CustomerSupport/src/baselines/tfidf_logreg.py)  
**Saved models:** `models/tfidf_intent_classifier.pkl`, `models/tfidf_escalation_classifier.pkl`

### Methodology
Two independent `scikit-learn` pipelines, each consisting of:

```
customer_message (raw text)
    ↓
TfidfVectorizer
    ↓
LogisticRegression
    ↓
intent label  /  escalation decision
```

**Only `customer_message` text is used as a feature.** No metadata (tweet ID, timestamp, author) is included.

---

## 6. Hyperparameters

### TF-IDF Vectorizer

| Hyperparameter | Value | Rationale |
| :--- | :--- | :--- |
| `ngram_range` | `(1, 2)` | Unigrams + bigrams capture compound terms like *"where is my"*, *"promo code"* |
| `max_features` | `50,000` | Balances vocabulary coverage vs memory/speed |
| `sublinear_tf` | `True` | Log-scaled TF reduces dominance of high-frequency stop words |
| `min_df` | `2` | Ignore terms appearing in fewer than 2 documents (noise reduction) |
| `strip_accents` | `"unicode"` | Normalize international characters |
| `analyzer` | `"word"` | Word-level tokenization |

### Logistic Regression (Intent — Multiclass)

| Hyperparameter | Value | Rationale |
| :--- | :--- | :--- |
| `C` | `1.0` | Default regularization strength |
| `solver` | `"lbfgs"` | Efficient for multiclass with dense features |
| `max_iter` | `1,000` | Sufficient iterations for convergence |
| `class_weight` | `"balanced"` | Automatically compensates for imbalanced class counts (payment_and_billing_issue has only 95 examples vs 3,000 for delivery_delay) |
| `random_state` | `42` | Reproducibility |

### Logistic Regression (Escalation — Binary)

Same parameters as above (binary classification is simpler — no multinomial strategy needed).

---

## 7. Internal Validation Performance (Training Split Only)

> [!NOTE]
> These are **internal validation results on 15% of training data** — **not** performance on the golden evaluation set. The golden dataset has not been touched.

### Intent Classifier (val_acc = 0.9567)

| Intent | Precision | Recall | F1 |
| :--- | :--- | :--- | :--- |
| `refund_inquiry` | 1.00 | 0.99 | 0.99 |
| `digital_and_device_troubleshooting` | 0.99 | 0.97 | 0.98 |
| `order_tracking_inquiry` | 0.97 | 0.98 | 0.98 |
| `general_product_and_service_faq` | 0.97 | 0.97 | 0.97 |
| `prime_membership_inquiry` | 0.97 | 0.99 | 0.98 |
| `promotion_and_discount_inquiry` | 0.96 | 0.98 | 0.97 |
| `delivery_delay` | 0.95 | 0.97 | 0.96 |
| `damaged_or_wrong_item` | 0.94 | 0.96 | 0.95 |
| `other_or_unsupported` | 0.94 | 0.81 | 0.87 |
| `driver_and_packaging_feedback` | 0.79 | 0.97 | 0.87 |
| `order_cancellation` | 0.80 | 1.00 | 0.89 |
| `payment_and_billing_issue` | 0.80 | 0.86 | 0.83 |
| `account_access_and_security` | 0.70 | 0.88 | 0.78 |
| **macro avg** | **0.91** | **0.95** | **0.93** |

### Escalation Classifier (val_acc = 0.9771)

| Decision | Precision | Recall | F1 |
| :--- | :--- | :--- | :--- |
| `AUTO_HANDLE` | 0.96 | 0.98 | 0.97 |
| `ESCALATE` | 0.99 | 0.97 | 0.98 |
| **macro avg** | **0.97** | **0.98** | **0.98** |

---

## 8. Why These Baselines Are Useful

1. **Lower bound comparison:** Any production-worthy LLM + RAG system must substantially outperform TF-IDF on the golden set — especially on nuanced borderline cases (e.g., *tracking vs delay*, *prime FAQ vs refund request*) that keyword-pattern classifiers systematically mishandle.

2. **Speed and cost benchmark:** TF-IDF inference runs in microseconds at zero API cost. If the LLM system only marginally improves accuracy, TF-IDF may be the better production choice.

3. **Sanity check:** If the RAG + LLM system performs *worse* than TF-IDF on the golden set, that is a red flag indicating broken prompting, hallucination, or evaluation methodology errors.

4. **Interpretability reference:** Logistic Regression coefficients can be inspected to verify that the model is learning legitimate signals (e.g., "refund" → `refund_inquiry`) vs spurious correlations.

---

## 9. Limitations

| Limitation | Impact |
| :--- | :--- |
| **Training labels are rule-based, not human-annotated** | Regex patterns may have introduced label noise in training. The golden evaluation set uses human-reviewed labels. |
| **Severe class imbalance remains** | `payment_and_billing_issue` (95 examples) vs `delivery_delay` (3,000). `class_weight='balanced'` mitigates but doesn't eliminate this. |
| **Twitter-specific language** | Training data consists of informal Twitter messages. Performance on cleaner, longer customer support emails may differ. |
| **No context window** | Each message is classified independently. Multi-turn conversation context is not used. |
| **Golden evaluation pending** | Internal validation accuracy on the training split is **optimistic** — actual golden dataset performance will be measured in Step 7 (Evaluation Harness). |

---

## 10. CLI Usage

### Build Training Data
```bash
python src/baselines/build_training_data.py
```

### Train All Baselines
```bash
python src/baselines/train_baselines.py
# or with custom paths:
python src/baselines/train_baselines.py --train-data data/training_data.jsonl --models-dir models/
```

### Run Unit Tests
```bash
python -m pytest tests/test_baselines.py -v
```
