import pandas as pd
import numpy as np

def assign_buckets(features_df, n_bins=10):
    df = features_df.copy()

    df["log_event_count"] = np.log1p(df["event_count"]) #normalize skewed distributions
    df["log_mean_gap"] = np.log1p(df["mean_gap"])

    df["event_bin"] = pd.qcut(df["log_event_count"], q=n_bins, labels=False, duplicates="drop")
    df["gap_bin"] = pd.qcut(df["log_mean_gap"], q=n_bins, labels=False, duplicates="drop")
    df["burst_bin"] = pd.qcut(df["burstiness"], q=n_bins, labels=False, duplicates="drop")

    df["bucket"] = list(zip(df["event_bin"], df["gap_bin"], df["burst_bin"]))
    return df

# def generate_candidate_pairs(bucketed_df, max_bucket_size=500):
#     candidate_pairs = []
#     skipped_buckets = 0

#     for bucket_key, group in bucketed_df.groupby("bucket"):
#         accounts = list(zip(group["account"], group["bank"]))
#         if len(accounts) < 2:
#             continue
#         if len(accounts) > max_bucket_size:
#             skipped_buckets += 1
#             continue
#         candidate_pairs.extend(combinations(accounts, 2)) #combinations(accounts, 2) creates unique pairs from a bucket

#     print(f"Buckets skipped for being too large: {skipped_buckets}")
#     return candidate_pairs

def generate_candidate_pairs_windowed(bucketed_df, sort_feature="mean_gap", window=10):
    candidate_pairs = []

    for bucket_key, group in bucketed_df.groupby("bucket"):
        if len(group) < 2:
            continue
        sorted_group = group.sort_values(sort_feature)
        accounts = list(zip(sorted_group["account"], sorted_group["bank"]))

        for i in range(len(accounts)):
            for j in range(i + 1, min(i + 1 + window, len(accounts))):
                candidate_pairs.append((accounts[i], accounts[j]))

    return candidate_pairs

