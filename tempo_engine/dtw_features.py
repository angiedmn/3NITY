import pandas as pd

FEATURE_GROUP_A = ["event_count", "mean_gap", "std_gap", "burstiness"]
FEATURE_GROUP_B = ["dtw_p10_distance", "dtw_median_distance", "dtw_fraction_similar"]


def aggregate_dtw_features(dtw_results, threshold_percentile=10):
    a_side = dtw_results[["account_a", "bank_a", "dtw_distance"]].rename(
        columns={"account_a": "account", "bank_a": "bank"}
    )
    b_side = dtw_results[["account_b", "bank_b", "dtw_distance"]].rename(
        columns={"account_b": "account", "bank_b": "bank"}
    )
    long_form = pd.concat([a_side, b_side], ignore_index=True)

    threshold = dtw_results["dtw_distance"].quantile(threshold_percentile / 100)
    print(f"Using similarity threshold: {threshold:.4f} (p{threshold_percentile} of observed distances)")

    grouped = long_form.groupby(["account", "bank"])["dtw_distance"]
    agg = grouped.agg(
        dtw_p10_distance=lambda x: x.quantile(0.10),
        dtw_median_distance="median",
        dtw_num_comparisons="count",
    ).reset_index()

    similar_counts = (
        long_form[long_form["dtw_distance"] <= threshold]
        .groupby(["account", "bank"])
        .size()
        .reindex(pd.MultiIndex.from_frame(agg[["account", "bank"]]), fill_value=0)
    )
    agg["dtw_num_similar"] = similar_counts.values
    agg["dtw_fraction_similar"] = agg["dtw_num_similar"] / agg["dtw_num_comparisons"]

    return agg


def build_final_feature_matrix(features_df, dtw_features):
    merged = features_df.merge(dtw_features, on=["account", "bank"], how="left")

    # accounts with no DTW comparisons: fill with "no similarity detected" values
    max_p10 = dtw_features["dtw_p10_distance"].max()
    max_median = dtw_features["dtw_median_distance"].max()
    merged["dtw_p10_distance"] = merged["dtw_p10_distance"].fillna(max_p10)
    merged["dtw_median_distance"] = merged["dtw_median_distance"].fillna(max_median)
    merged["dtw_num_comparisons"] = merged["dtw_num_comparisons"].fillna(0)
    merged["dtw_num_similar"] = merged["dtw_num_similar"].fillna(0)
    merged["dtw_fraction_similar"] = merged["dtw_fraction_similar"].fillna(0.0)

    return merged