import pandas as pd
from config import DATA_PATH
import os
import psycopg2
import pandas as pd
def load_data():
    df = pd.read_csv(
        DATA_PATH,
        dtype={
            "From Bank": str,
            "Account": str,
            "To Bank": str,
            "Account.1": str
        }
    )

    df.columns = [
        "Timestamp",
        "From_Bank",
        "Account",
        "To_Bank",
        "Account_1",
        "Amount_Received",
        "Receiving_Currency",
        "Amount_Paid",
        "Payment_Currency",
        "Payment_Format",
        "Is_Laundering"
    ]

    # in load_data, after the rename:
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], format="%Y/%m/%d %H:%M")

    return df

DB_URL = os.environ.get("SUPABASE_DB_URL")

def load_tempo_sequence(account_id: str) -> pd.DataFrame:
    """Fetches real-time transaction ledger for a specific account from Supabase."""
    conn = psycopg2.connect(DB_URL)
    try:
        with conn.cursor() as cur:
            query = """
                SELECT timestamp, sender_account, receiver_account, amount_usd 
                FROM tempo_ledger 
                WHERE sender_account = %s OR receiver_account = %s
                ORDER BY timestamp ASC
            """
            cur.execute(query, (account_id, account_id))
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            
            df = pd.DataFrame(rows, columns=columns)
            if not df.empty:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
            return df
    finally:
        conn.close()