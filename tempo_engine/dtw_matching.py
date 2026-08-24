from dtaidistance import dtw
import numpy as np
import pandas as pd
import time

def compute_dtw_for_candidates(candidate_pairs, activity_vectors):
    records = []
    n_fallback = 0
    start = time.time()

    for i, (acct_a, acct_b) in enumerate(candidate_pairs):
        vec_a = np.asarray(activity_vectors[acct_a], dtype=np.float64)
        vec_b = np.asarray(activity_vectors[acct_b], dtype=np.float64)

        distance = dtw.distance_fast(vec_a, vec_b) #distance fast is C path -> faster for M's trancs

        if not np.isfinite(distance):
            distance = dtw.distance(vec_a, vec_b)  # pure-Python fallback, correctness > speed here
            n_fallback += 1

        records.append({
            "account_a": acct_a[0], "bank_a": acct_a[1],
            "account_b": acct_b[0], "bank_b": acct_b[1],
            "dtw_distance": distance,
        })

        if (i + 1) % 200000 == 0:
            elapsed = time.time() - start
            print(f"{i+1}/{len(candidate_pairs)} pairs done, {elapsed:.1f}s elapsed")

    print(f"Total fallbacks to pure-Python distance: {n_fallback} / {len(candidate_pairs)}")
    return pd.DataFrame(records)
