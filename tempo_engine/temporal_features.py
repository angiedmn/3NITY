
import numpy as np
import pandas as pd

def compute_temporal_features(sequences):
    records = []
    for (account, bank), events in sequences.items():
        n = len(events)
        if n < 2:
            # not enough data to compute gaps — decide how you want to handle this
            # (skip the account entirely, or record NaNs — think about which is safer for Isolation Forest later)
            continue

        timestamps = [e["timestamp"] for e in events]
        gaps = [
            (timestamps[i + 1] - timestamps[i]).total_seconds()
            for i in range(len(timestamps) - 1)
        ]

        mean_gap = float(np.mean(gaps))
        std_gap = float(np.std(gaps)) if len(gaps) >= 2 else 0.0

        denom = std_gap + mean_gap
        burstiness = (std_gap - mean_gap) / denom if denom > 0 else 0.0

        records.append({
            "account": account,
            "bank": bank,
            "event_count": n,
            "mean_gap": mean_gap,
            "std_gap": std_gap,
            "burstiness": burstiness,
        })

    return pd.DataFrame(records)

def build_activity_vectors(sequences, start_time, end_time, bin_size="h"): #bin size -> per Hour
    bin_edges = pd.date_range(start=start_time, end=end_time, freq=bin_size)
    n_bins = len(bin_edges) - 1

    vectors = {}
    for key, events in sequences.items():
        timestamps = pd.to_datetime([e["timestamp"] for e in events])
        counts, _ = np.histogram(timestamps.astype("int64"), bins=bin_edges.astype("int64"))
        vectors[key] = counts.astype(np.float64)

    return vectors, n_bins
