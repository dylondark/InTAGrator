from sentence_transformers import SentenceTransformer
from sentence_transformers.cross_encoder import CrossEncoder
import numpy as np
from numpy.linalg import norm

# ── Config ────────────────────────────────────────────────────────────────────
BI_MODEL      = "all-MiniLM-L6-v2"
CROSS_MODEL   = "cross-encoder/ms-marco-MiniLM-L-6-v2"
BI_THRESHOLD  = 0.85   # cosine similarity threshold for bi-encoder
CE_THRESHOLD  = 0.0    # cross-encoder outputs a raw logit; 0.0 is a reasonable starting point

bi_encoder    = SentenceTransformer(BI_MODEL)
cross_encoder = CrossEncoder(CROSS_MODEL)

# ── Test pairs (string_a, string_b, expected_match) ───────────────────────────
test_pairs = [
    # --- True aliases (should match) ---
    ("Jay-Z",               "Jay Z",                True),   # punctuation variant
    ("The Weeknd",          "Abel Tesfaye",          True),   # stage name vs real name
    ("Eminem",              "Marshall Mathers",      True),   # stage name vs real name
    ("Nicki Minaj",         "Onika Maraj",           True),   # stage name vs real name
    ("Lorde",               "Ella Yelich-O'Connor",  True),   # stage name vs real name

    # --- Related but NOT aliases (should not match) ---
    ("Freddie Mercury",     "Queen",                 False),  # member ↔ band
    ("Beyoncé",             "Destiny's Child",       False),  # member ↔ group
    ("Slash",               "Guns N' Roses",         False),  # member ↔ band

    # --- Clearly unrelated (should not match) ---
    ("Taylor Swift",        "Kendrick Lamar",        False),
    ("The Beatles",         "The Rolling Stones",    False),
    ("Adele",               "Bruno Mars",            False),
]

# ── Helpers ───────────────────────────────────────────────────────────────────
def bi_score(a: str, b: str) -> float:
    va = bi_encoder.encode(a, normalize_embeddings=True)
    vb = bi_encoder.encode(b, normalize_embeddings=True)
    return float(np.dot(va, vb) / (norm(va) * norm(vb)))

def ce_score(a: str, b: str) -> float:
    return float(cross_encoder.predict([[a, b]])[0])

# ── Run ───────────────────────────────────────────────────────────────────────
col_w = 22
header = (
    f"{'String A':<{col_w}} {'String B':<{col_w}}"
    f" {'Expected':<10}"
    f" {'BiEnc':>7} {'BiEnc?':>9}"
    f" {'CEnc':>7} {'CEnc?':>9}"
)
divider = "─" * len(header)

print(f"Bi-Encoder  : {BI_MODEL}  (threshold: {BI_THRESHOLD})")
print(f"Cross-Encoder: {CROSS_MODEL}  (threshold: {CE_THRESHOLD})\n")
print(header)
print(divider)

bi_correct = ce_correct = 0
for str_a, str_b, expected in test_pairs:
    bs = bi_score(str_a, str_b)
    cs = ce_score(str_a, str_b)

    bi_pred = bs >= BI_THRESHOLD
    ce_pred = cs >= CE_THRESHOLD

    bi_correct += int(bi_pred == expected)
    ce_correct += int(ce_pred == expected)

    exp_label = "MATCH" if expected else "NO MATCH"
    print(
        f"{str_a:<{col_w}} {str_b:<{col_w}}"
        f" {exp_label:<10}"
        f" {bs:>7.4f} {'✓' if bi_pred == expected else '✗':>9}"
        f" {cs:>7.3f} {'✓' if ce_pred == expected else '✗':>9}"
    )

n = len(test_pairs)
print(divider)
print(f"\n{'Bi-Encoder  accuracy:':<25} {bi_correct}/{n} ({100*bi_correct/n:.0f}%)")
print(f"{'Cross-Encoder accuracy:':<25} {ce_correct}/{n} ({100*ce_correct/n:.0f}%)")
