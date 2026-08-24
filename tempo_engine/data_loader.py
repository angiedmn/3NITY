import pandas as pd
from config import DATA_PATH

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
