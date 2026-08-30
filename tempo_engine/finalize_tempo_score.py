import numpy as np


def finalize_tempo_score(scored_features):
    """
    Final, exportable Tempo score: 0-1 scale, min-max normalized from the
    inverted Isolation Forest decision_function — same scaling approach as
    Gait_Score, so the two are directly comparable/combinable downstream.

    FIXED: added `entity_id`, the canonical "<bank>:<account>" string used
    everywhere else in 3NITY (Gait telemetry keys, Mirage registry keys,
    the gateway's TransactionRequest). Previously this only exposed
    separate `account`/`bank` columns, which nothing outside this batch
    pipeline could join against.
    """
    raw = scored_features["tempo_anomaly_score"]
    min_v, max_v = raw.min(), raw.max()

    if max_v - min_v < 1e-9:
        normalized = np.zeros_like(raw)
    else:
        normalized = (raw - min_v) / (max_v - min_v)

    output = scored_features[["account", "bank"]].copy()
    output["entity_id"] = output["bank"].astype(str) + ":" + output["account"].astype(str)
    output["Tempo_Score"] = normalized
    output["tempo_is_anomaly"] = scored_features["tempo_is_anomaly"]

    return output