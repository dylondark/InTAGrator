from sentence_transformers import SentenceTransformer
import numpy as np
from numpy.linalg import norm

# ── Config ────────────────────────────────────────────────────────────────────
MODEL     = "all-MiniLM-L6-v2"  
THRESHOLD = 0.85               

model = SentenceTransformer(MODEL)

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
def get_embedding(text: str) -> np.ndarray:
    return model.encode(text, normalize_embeddings=True)

def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (norm(a) * norm(b)))

# ── Run ───────────────────────────────────────────────────────────────────────
print(f"Model : {MODEL}")
print(f"Threshold : {THRESHOLD}\n")
print(f"{'String A':<20} {'String B':<20} {'Score':>7}  {'Predicted':>10}  {'Expected':>10}  {'Correct':>8}")
print("─" * 85)

correct = 0
for str_a, str_b, expected in test_pairs:
    vec_a = get_embedding(str_a)
    vec_b = get_embedding(str_b)
    score = cosine_sim(vec_a, vec_b)
    predicted = score >= THRESHOLD
    is_correct = predicted == expected
    correct += int(is_correct)

    print(
        f"{str_a:<20} {str_b:<20} {score:>7.4f}  "
        f"{'MATCH' if predicted else 'NO MATCH':>10}  "
        f"{'MATCH' if expected else 'NO MATCH':>10}  "
        f"{'✓' if is_correct else '✗':>8}"
    )

print("─" * 85)
print(f"\nAccuracy: {correct}/{len(test_pairs)} ({100*correct/len(test_pairs):.0f}%)")