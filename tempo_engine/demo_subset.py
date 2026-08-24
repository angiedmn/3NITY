import numpy as np
import pandas as pd

def get_laundering_account_ids(df):
    return set(
        zip(df.loc[df["Is_Laundering"] == 1, "Account"], df.loc[df["Is_Laundering"] == 1, "From_Bank"])
    ) | set(
        zip(df.loc[df["Is_Laundering"] == 1, "Account_1"], df.loc[df["Is_Laundering"] == 1, "To_Bank"])
    )


def build_demo_subset(features_df, laundering_account_ids, n_normal=5000, seed=42):
    is_laundering = features_df.apply(
        lambda r: (r["account"], r["bank"]) in laundering_account_ids, axis=1
    )
    laundering_subset = features_df[is_laundering]
    normal_pool = features_df[~is_laundering]

    normal_sample = normal_pool.sample(n=min(n_normal, len(normal_pool)), random_state=seed)

    subset = pd.concat([laundering_subset, normal_sample], ignore_index=True)
    print(f"Laundering accounts in subset: {len(laundering_subset)}")
    print(f"Normal accounts in subset: {len(normal_sample)}")
    print(f"Total subset size: {len(subset)}")
    return subset

