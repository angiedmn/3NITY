import pandas as pd
import numpy as np
from data_loader import load_data
from sequences import build_account_sequences
from temporal_features import compute_temporal_features, build_activity_vectors
from demo_subset import get_laundering_account_ids, build_demo_subset
from candidates import assign_buckets, generate_candidate_pairs_windowed
from dtw_matching import compute_dtw_for_candidates
from isolation_forest import run_isolation_forest, evaluate_against_known_labels
from dtw_features import aggregate_dtw_features, build_final_feature_matrix, FEATURE_GROUP_A, FEATURE_GROUP_B



df = load_data()
sequences = build_account_sequences(df)
features_df = compute_temporal_features(sequences)

# demo scoping
laundering_account_ids = get_laundering_account_ids(df)
features_df = build_demo_subset(features_df, laundering_account_ids, n_normal=5000)
# end demo scoping

bucketed_df = assign_buckets(features_df)
candidate_pairs = generate_candidate_pairs_windowed(bucketed_df, window=10)
print(f"Total candidate pairs: {len(candidate_pairs)}")

start_time = df["Timestamp"].min().floor("h")
end_time = df["Timestamp"].max().ceil("h")

raw_vectors, n_bins = build_activity_vectors(sequences, start_time, end_time)
dtw_results = compute_dtw_for_candidates(candidate_pairs, raw_vectors)


# diagnostic only — not part of the pipeline, run manually after dtw_results exists

# zero_pairs = dtw_results[dtw_results["dtw_distance"] == 0]
# print(f"Zero-distance pairs: {len(zero_pairs)} / {len(dtw_results)} ({len(zero_pairs)/len(dtw_results):.2%})")

# # merge in event_count for both sides of each zero-distance pair
# ec = features_df.set_index(["account", "bank"])["event_count"]

# zero_pairs = zero_pairs.copy()
# zero_pairs["event_count_a"] = zero_pairs.set_index(["account_a", "bank_a"]).index.map(ec)
# zero_pairs["event_count_b"] = zero_pairs.set_index(["account_b", "bank_b"]).index.map(ec)

# print(zero_pairs[["event_count_a", "event_count_b"]].describe())


dtw_features = aggregate_dtw_features(
    dtw_results,
    event_counts=features_df.set_index(["account", "bank"])["event_count"],
)
# print(dtw_features.shape)
# print(dtw_features.describe())
final_features = build_final_feature_matrix(features_df, dtw_features)
# print(final_features.shape)
# print(final_features.isna().sum())

scored_features = run_isolation_forest(final_features, contamination=0.02)
print(scored_features["tempo_anomaly_score"].describe())
print(scored_features["tempo_is_anomaly"].value_counts())

scored_features = evaluate_against_known_labels(scored_features, laundering_account_ids)
scored_features["is_known_laundering"] = scored_features.apply(
    lambda r: (r["account"], r["bank"]) in laundering_account_ids, axis=1
)
print(scored_features.groupby("is_known_laundering")["tempo_anomaly_score"].describe())

flagged = scored_features[scored_features["tempo_is_anomaly"]]
print(f"Flagged accounts: {len(flagged)}")
print(f"Of those, known laundering: {flagged['is_known_laundering'].sum()}")
print(f"Precision of flagged set: {flagged['is_known_laundering'].mean():.4f}")
print(f"Base rate in subset: {scored_features['is_known_laundering'].mean():.4f}")

feature_cols = FEATURE_GROUP_A + FEATURE_GROUP_B
print(scored_features.groupby("is_known_laundering")[feature_cols].mean())






############




#




















