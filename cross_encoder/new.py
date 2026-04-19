import json
import random
from pathlib import Path
from sklearn.model_selection import train_test_split
from sentence_transformers.cross_encoder import CrossEncoder
from sentence_transformers.cross_encoder.evaluation import CEBinaryClassificationEvaluator
from sentence_transformers import InputExample
from torch.utils.data import DataLoader

# ── Config ────────────────────────────────────────────────────────────────────
CROSS_MODEL       = "cross-encoder/ms-marco-MiniLM-L-6-v2"
OUTPUT_MODEL_PATH = "./finetuned-alias-crossencoder"
DATA_FILE         = "./mb_page_0.json"   # <-- put mb_page_0.json in same folder as this script

NEGATIVE_RATIO    = 1      # negatives per positive (1 = balanced dataset)
TEST_SIZE         = 0.2
RANDOM_SEED       = 42
EPOCHS            = 50
BATCH_SIZE        = 16
THRESHOLD         = 0.0    # decision boundary for both models (raw logit)

random.seed(RANDOM_SEED)

# ── Step 1: Load data ─────────────────────────────────────────────────────────
print(f"[data] Loading {DATA_FILE}...")
with open(DATA_FILE) as f:
    artist_aliases = json.load(f)

print(f"[data] {len(artist_aliases)} artists loaded")

# ── Step 2: Build labeled pairs ───────────────────────────────────────────────
positives = []
for artist, aliases in artist_aliases.items():
    for alias in aliases:
        positives.append((artist, alias, 1))

all_names = list(artist_aliases.keys())
n_negatives = len(positives) * NEGATIVE_RATIO
negatives = []
attempts = 0
while len(negatives) < n_negatives and attempts < n_negatives * 10:
    a, b = random.sample(all_names, 2)
    if b not in artist_aliases.get(a, []) and a not in artist_aliases.get(b, []):
        negatives.append((a, b, 0))
    attempts += 1

pairs = positives + negatives
random.shuffle(pairs)
print(f"[pairs] {len(positives)} positives + {len(negatives)} negatives = {len(pairs)} total")

# ── Step 3: Split ─────────────────────────────────────────────────────────────
train_pairs, test_pairs = train_test_split(pairs, test_size=TEST_SIZE, random_state=RANDOM_SEED)
print(f"[split] {len(train_pairs)} train / {len(test_pairs)} test")

# ── Step 4: Fine-tune ─────────────────────────────────────────────────────────
print(f"\n[train] Loading base model: {CROSS_MODEL}")
model = CrossEncoder(CROSS_MODEL, num_labels=1)

train_samples = [InputExample(texts=[a, b], label=float(lbl)) for a, b, lbl in train_pairs]
train_loader  = DataLoader(train_samples, shuffle=True, batch_size=BATCH_SIZE)

test_samples  = [InputExample(texts=[a, b], label=float(lbl)) for a, b, lbl in test_pairs]
evaluator     = CEBinaryClassificationEvaluator.from_input_examples(test_samples, name="test")

print(f"[train] Fine-tuning for {EPOCHS} epochs on {len(train_samples)} samples...")
model.fit(
    train_dataloader=train_loader,
    evaluator=evaluator,
    epochs=EPOCHS,
    evaluation_steps=200,
    output_path=OUTPUT_MODEL_PATH,
)
print(f"[train] Done. Best model saved to {OUTPUT_MODEL_PATH}")

# ── Step 5: Evaluate base vs fine-tuned ──────────────────────────────────────
print("\n[eval] Loading base model for comparison...")
base_model   = CrossEncoder(CROSS_MODEL)
tuned_model  = CrossEncoder(OUTPUT_MODEL_PATH)

col = 30
header = (
    f"{'String A':<{col}} {'String B':<{col}} {'Expected':<10}"
    f" {'Base':>8} {'Base?':>6}"
    f" {'Tuned':>8} {'Tuned?':>7}"
)
divider = "─" * len(header)

print("\n" + divider)
print(header)
print(divider)

base_correct = tuned_correct = 0
for a, b, expected in test_pairs:
    bs = float(base_model.predict([[a, b]])[0])
    ts = float(tuned_model.predict([[a, b]])[0])

    base_pred  = bs >= THRESHOLD
    tuned_pred = ts >= THRESHOLD

    base_correct  += int(base_pred  == bool(expected))
    tuned_correct += int(tuned_pred == bool(expected))

# Print a sample of 30 for readability
print(f"(showing 30 of {len(test_pairs)} test pairs)\n")
for a, b, expected in test_pairs[:30]:
    bs = float(base_model.predict([[a, b]])[0])
    ts = float(tuned_model.predict([[a, b]])[0])
    base_pred  = bs >= THRESHOLD
    tuned_pred = ts >= THRESHOLD
    exp_label  = "MATCH" if expected else "NO MATCH"
    print(
        f"{a:<{col}} {b:<{col}} {exp_label:<10}"
        f" {bs:>8.3f} {'✓' if base_pred == bool(expected) else '✗':>6}"
        f" {ts:>8.3f} {'✓' if tuned_pred == bool(expected) else '✗':>7}"
    )

n = len(test_pairs)
print(divider)
print(f"\n{'Base model accuracy:':<30} {base_correct}/{n} ({100*base_correct/n:.1f}%)")
print(f"{'Fine-tuned model accuracy:':<30} {tuned_correct}/{n} ({100*tuned_correct/n:.1f}%)")