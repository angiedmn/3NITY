"""
data_loader.py
--------------
Loads the Kaggle IBM AML transactions CSV and extracts a clean list
of unique account IDs to attach synthetic gait telemetry to.

Kaggle "IBM Transactions for Anti Money Laundering (AML)" dataset
typically has columns like:
    Timestamp, From Bank, Account, To Bank, Account.1,
    Amount Received, Receiving Currency, Amount Paid, Payment Currency,
    Payment Format, Is Laundering

The two account columns are usually named 'Account' (sender) and
'Account.1' (receiver) because of how pandas handles duplicate headers.
This loader is defensive about column naming since Kaggle has shipped
slightly different header variants across dataset versions.
"""

import pandas as pd
from pathlib import Path

# Candidate column names seen across different releases of the dataset
SENDER_ACCOUNT_CANDIDATES = ["Account", "From Account", "Sender Account"]
RECEIVER_ACCOUNT_CANDIDATES = ["Account.1", "To Account", "Receiver Account"]


def _find_column(df: pd.DataFrame, candidates: list[str]) -> str:
    for c in candidates:
        if c in df.columns:
            return c
    raise ValueError(
        f"None of the expected columns {candidates} found. "
        f"Actual columns: {list(df.columns)}"
    )

#check if files exist and load them
def load_transactions(csv_path: str, nrows: int | None = None) -> pd.DataFrame:
    """Load the raw Kaggle AML transactions CSV."""
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Could not find {csv_path}. Download the 'IBM Transactions for "
            f"Anti Money Laundering (AML)' dataset from Kaggle and point "
            f"this function at the extracted CSV."
        )
    df = pd.read_csv(path, nrows=nrows)
    return df

#loads the transactions and finds the correct headers
def load_account_ids(csv_path: str, nrows: int | None = None) -> pd.Series:
    """
    Load unique account IDs from the Kaggle IBM AML transactions CSV.
    Combines both sender and receiver account columns since either side
    of a transaction is a valid account to attach telemetry to.
    """
    df = load_transactions(csv_path, nrows=nrows)

    sender_col = _find_column(df, SENDER_ACCOUNT_CANDIDATES)
    receiver_col = _find_column(df, RECEIVER_ACCOUNT_CANDIDATES)

    accounts = pd.concat([df[sender_col], df[receiver_col]], ignore_index=True)
    unique_accounts = accounts.dropna().drop_duplicates().reset_index(drop=True)
    unique_accounts.name = "account_id"
    return unique_accounts

def load_laundering_labels(csv_path: str, nrows: int | None = None) -> pd.DataFrame:
    """
    Optional helper: pull the 'Is Laundering' ground-truth flag per
    transaction, aggregated up to the account level (an account is
    flagged 'suspect' if it appears in ANY laundering-labeled transaction).
    Useful later for cross-checking Gait_Score against ground truth.
    """
    df = load_transactions(csv_path, nrows=nrows)
    if "Is Laundering" not in df.columns:
        raise ValueError("'Is Laundering' column not found in this CSV.")

    sender_col = _find_column(df, SENDER_ACCOUNT_CANDIDATES)
    receiver_col = _find_column(df, RECEIVER_ACCOUNT_CANDIDATES)

    sender_flags = df[[sender_col, "Is Laundering"]].rename(
        columns={sender_col: "account_id"}
    )
    receiver_flags = df[[receiver_col, "Is Laundering"]].rename(
        columns={receiver_col: "account_id"}
    )
    combined = pd.concat([sender_flags, receiver_flags], ignore_index=True)
    account_flags = (
        combined.groupby("account_id")["Is Laundering"].max().reset_index()
    )
    return account_flags


if __name__ == "__main__":
    import sys

    csv_path = sys.argv[1] if len(sys.argv) > 1 else "HI-Small_Trans.csv"
    ids = load_account_ids(csv_path, nrows=200_000)
    print(f"Loaded {len(ids)} unique account IDs")
    print(ids.head())