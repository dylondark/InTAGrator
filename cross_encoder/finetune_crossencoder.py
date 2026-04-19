import requests
import random
import time
import json
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from sentence_transformers.cross_encoder import CrossEncoder
from sentence_transformers.cross_encoder.evaluation import CEBinaryClassificationEvaluator
import torch

# ── Config ────────────────────────────────────────────────────────────────────
CROSS_MODEL       = "cross-encoder/ms-marco-MiniLM-L-6-v2"
OUTPUT_MODEL_PATH = "./finetuned-alias-crossencoder"
DATA_CACHE        = "./musicbrainz_data.json"

MB_LIMIT          = 100   # artists to fetch per request (max 100)
MB_PAGES          = 5     # number of pages → 500 artists total
MIN_ALIASES       = 1     # only keep artists with at least this many aliases
NEGATIVE_RATIO    = 1     # negatives per positive (1 = balanced)
TEST_SIZE         = 0.2
RANDOM_SEED       = 42
EPOCHS            = 5
BATCH_SIZE        = 16
BASE_THRESHOLD    = 0.0   # threshold for base model evaluation
TUNED_THRESHOLD   = 0.0   # threshold for fine-tuned model evaluation

random.seed(RANDOM_SEED)

# ── Step 1: Fetch artists + aliases from MusicBrainz ─────────────────────────
def fetch_page(url: str, headers: dict, retries: int = 5) -> dict | None:
    """Fetch a single URL with exponential backoff on SSL/connection errors."""
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            print(f"  [!] HTTP {resp.status_code}, retrying...")
        except Exception as e:
            wait = 2 ** attempt
            print(f"  [!] Attempt {attempt+1} failed ({e.__class__.__name__}), retrying in {wait}s...")
            time.sleep(wait)
    return None

def fetch_musicbrainz_artists(pages: int = MB_PAGES, limit: int = MB_LIMIT) -> dict:
    """
    Returns { artist_name: [alias1, alias2, ...] }
    Only includes artists that have at least MIN_ALIASES aliases.
    Caches each page individually so crashes don't lose progress.
    """
    if Path(DATA_CACHE).exists():
        print(f"[data] Loading cached data from {DATA_CACHE}")
        with open(DATA_CACHE) as f:
            return json.load(f)

    print(f"[data] Fetching artists from MusicBrainz ({pages} pages × {limit} artists)...")
    headers = {"User-Agent": "AliasResearchProject/1.0 (research@example.com)"}
    artist_aliases = {}

    for page in range(pages):
        page_cache = Path(f"./mb_page_{page}.json")

        # Use per-page cache if available
        if page_cache.exists():
            print(f"  [data] Page {page+1} loaded from cache")
            with open(page_cache) as f:
                artist_aliases.update(json.load(f))
            continue

        offset = page * limit
        url = (
            f"https://musicbrainz.org/ws/2/artist"
            f"?query=type:person OR type:group&limit={limit}&offset={offset}&fmt=json"
        )

        data = fetch_page(url, headers)
        if data is None:
            print(f"  [!] Page {page+1} failed after all retries, skipping.")
            continue

        page_data = {}
        for artist in data.get("artists", []):
            name = artist.get("name", "").strip()
            aliases = [
                a["name"].strip()
                for a in artist.get("aliases", [])
                if a.get("name", "").strip() and a["name"].strip().lower() != name.lower()
            ]
            if len(aliases) >= MIN_ALIASES:
                page_data[name] = aliases

        # Cache this page
        with open(page_cache, "w") as f:
            json.dump(page_data, f, indent=2)

        artist_aliases.update(page_data)
        print(f"  [data] Page {page+1}/{pages} — {len(artist_aliases)} artists with aliases so far")
        time.sleep(1.1)  # MusicBrainz rate limit: 1 req/sec

    print(f"[data] Done. {len(artist_aliases)} artists with aliases.")
    with open(DATA_CACHE, "w") as f:
        json.dump(artist_aliases, f, indent=2)
    print(f"[data] Cached to {DATA_CACHE}")
    return artist_aliases

# ── Step 2: Build labeled pairs ───────────────────────────────────────────────
def build_pairs(artist_aliases: dict) -> list[tuple[str, str, int]]:
    """Returns list of (string_a, string_b, label) where label is 1=match, 0=no match."""
    positives = []
    for artist, aliases in artist_aliases.items():
        for alias in aliases:
            positives.append((artist, alias, 1))

    # Build negatives by randomly pairing different artists
    all_names = list(artist_aliases.keys())
    n_negatives = len(positives) * NEGATIVE_RATIO
    negatives = []
    attempts = 0
    while len(negatives) < n_negatives and attempts < n_negatives * 10:
        a, b = random.sample(all_names, 2)
        # Make sure b is not an alias of a and vice versa
        if b not in artist_aliases.get(a, []) and a not in artist_aliases.get(b, []):
            negatives.append((a, b, 0))
        attempts += 1

    pairs = positives + negatives
    random.shuffle(pairs)
    print(f"[pairs] {len(positives)} positives, {len(negatives)} negatives → {len(pairs)} total pairs")
    return pairs

# ── Step 3: Fine-tune cross-encoder ──────────────────────────────────────────
def finetune(train_pairs, test_pairs):
    from sentence_transformers.cross_encoder import CrossEncoder
    from torch.utils.data import DataLoader
    from sentence_transformers import InputExample

    print(f"\n[train] Loading base model: {CROSS_MODEL}")
    model = CrossEncoder(CROSS_MODEL, num_labels=1)

    train_samples = [InputExample(texts=[a, b], label=float(label)) for a, b, label in train_pairs]
    train_loader  = DataLoader(train_samples, shuffle=True, batch_size=BATCH_SIZE)

    test_samples  = [InputExample(texts=[a, b], label=float(label)) for a, b, label in test_pairs]
    evaluator     = CEBinaryClassificationEvaluator.from_input_examples(test_samples, name="test")

    print(f"[train] Fine-tuning for {EPOCHS} epochs on {len(train_samples)} samples...")
    model.fit(
        train_dataloader=train_loader,
        evaluator=evaluator,
        epochs=EPOCHS,
        evaluation_steps=100,
        output_path=OUTPUT_MODEL_PATH,
    )
    print(f"[train] Done. Model saved to {OUTPUT_MODEL_PATH}")
    return model

# ── Step 4: Evaluate both models ──────────────────────────────────────────────
def evaluate(test_pairs, tuned_model):
    base_model = CrossEncoder(CROSS_MODEL)

    print("\n" + "─" * 100)
    col = 28
    print(f"{'String A':<{col}} {'String B':<{col}} {'Expected':<10} {'Base':>7} {'Base?':>7} {'Tuned':>8} {'Tuned?':>8}")
    print("─" * 100)

    base_correct = tuned_correct = 0
    for a, b, expected in test_pairs[:50]:  # print first 50 for readability
        base_s  = float(base_model.predict([[a, b]])[0])
        tuned_s = float(tuned_model.predict([[a, b]])[0])

        base_pred  = base_s  >= BASE_THRESHOLD
        tuned_pred = tuned_s >= TUNED_THRESHOLD

        base_correct  += int(base_pred  == bool(expected))
        tuned_correct += int(tuned_pred == bool(expected))

        exp_label = "MATCH" if expected else "NO MATCH"
        print(
            f"{a:<{col}} {b:<{col}} {exp_label:<10}"
            f" {base_s:>7.3f} {'✓' if base_pred == bool(expected) else '✗':>7}"
            f" {tuned_s:>8.3f} {'✓' if tuned_pred == bool(expected) else '✗':>8}"
        )

    n = len(test_pairs)
    # Re-run full evaluation for accuracy (all pairs, not just printed 50)
    all_base_correct = all_tuned_correct = 0
    for a, b, expected in test_pairs:
        base_s  = float(base_model.predict([[a, b]])[0])
        tuned_s = float(tuned_model.predict([[a, b]])[0])
        all_base_correct  += int((base_s  >= BASE_THRESHOLD)  == bool(expected))
        all_tuned_correct += int((tuned_s >= TUNED_THRESHOLD) == bool(expected))

    print("─" * 100)
    print(f"\n{'Base model accuracy:':<30} {all_base_correct}/{n} ({100*all_base_correct/n:.1f}%)")
    print(f"{'Fine-tuned model accuracy:':<30} {all_tuned_correct}/{n} ({100*all_tuned_correct/n:.1f}%)")

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # 1. Data
    artist_aliases = fetch_musicbrainz_artists()
    pairs = build_pairs(artist_aliases)

    # 2. Split
    train_pairs, test_pairs = train_test_split(pairs, test_size=TEST_SIZE, random_state=RANDOM_SEED)
    print(f"[split] {len(train_pairs)} train / {len(test_pairs)} test")

    # 3. Fine-tune
    tuned_model = finetune(train_pairs, test_pairs)

    # 4. Evaluate
    evaluate(test_pairs, tuned_model)