import pandas as pd

FEATURE_GROUP_A = ["event_count", "mean_gap", "std_gap", "burstiness"]
FEATURE_GROUP_B = ["dtw_p10_distance", "dtw_median_distance", "dtw_fraction_similar"]


def aggregate_dtw_features(dtw_results, event_counts, threshold_percentile=10, min_event_count=5):
    a_side = dtw_results[["account_a", "bank_a", "dtw_distance"]].rename(
        columns={"account_a": "account", "bank_a": "bank"}
    )
    b_side = dtw_results[["account_b", "bank_b", "dtw_distance"]].rename(
        columns={"account_b": "account", "bank_b": "bank"}
    )
    long_form = pd.concat([a_side, b_side], ignore_index=True)

    # threshold computed only from pairs where BOTH sides clear min_event_count,
    # so degenerate low-activity ties (near-empty vectors tying at distance 0)
    # don't drag the threshold down artificially
    ec_a = dtw_results.set_index(["account_a", "bank_a"]).index.map(event_counts)
    ec_b = dtw_results.set_index(["account_b", "bank_b"]).index.map(event_counts)
    eligible_mask = (ec_a >= min_event_count) & (ec_b >= min_event_count)
    eligible_distances = dtw_results.loc[eligible_mask, "dtw_distance"]

    if len(eligible_distances) == 0:
        # fallback: don't crash if the floor excludes everything, just use full population
        eligible_distances = dtw_results["dtw_distance"]

    threshold = eligible_distances.quantile(threshold_percentile / 100)
    print(f"Using similarity threshold: {threshold:.4f} (p{threshold_percentile} of pairs with event_count >= {min_event_count})")

    # membership test (dtw_num_similar) still runs against the FULL population,
    # only the threshold value itself is computed on the filtered subset
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