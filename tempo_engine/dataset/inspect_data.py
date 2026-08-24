
import pandas as pd

df = pd.read_csv("HI-Small_Trans.csv")
pat = pd.read_csv("HI-Small_Patterns.txt", sep='\t')
print(pat.head())
print(df.dtypes)
print(df.head())

print(df.columns.tolist())
print(pd.read_csv("HI-Small_Trans.csv")["Is Laundering"].value_counts())

df["Timestamp"] = pd.to_datetime(df["Timestamp"], format="%Y/%m/%d %H:%M")

# 1. Timestamp granularity
print("Unique second values:", df["Timestamp"].dt.second.unique())
print("Time range:", df["Timestamp"].min(), "to", df["Timestamp"].max())
print("Duplicate timestamp count (exact same minute, any accounts):", df["Timestamp"].duplicated().sum())

# 2. Account uniqueness across banks
acct_bank_pairs = df[["Account", "From Bank"]].drop_duplicates()
print("Unique Account strings:", df["Account"].nunique())
print("Unique (Account, Bank) pairs:", len(acct_bank_pairs))

# 3. Payment format / currency diversity
print(df["Payment Format"].value_counts())
print(df["Receiving Currency"].value_counts())

# 4. Account-level label rollup
laundering_accounts = set(df.loc[df["Is Laundering"] == 1, "Account"]) | \
                       set(df.loc[df["Is Laundering"] == 1, "Account.1"])

print("Accounts touching ≥1 laundering transaction:", len(laundering_accounts))

print("Total unique accounts (sender or receiver):",
      len(set(df["Account"]) | set(df["Account.1"])))


sender_accounts = set(df["Account"])
receiver_accounts = set(df["Account.1"])

only_sender = sender_accounts - receiver_accounts
only_receiver = receiver_accounts - sender_accounts
both = sender_accounts & receiver_accounts

print("Sender-only accounts:", len(only_sender))
print("Receiver-only accounts:", len(only_receiver))
print("Both sender and receiver:", len(both))

# does laundering concentrate in a particular role?
laundering_senders = set(df.loc[df["Is Laundering"] == 1, "Account"])
laundering_receivers = set(df.loc[df["Is Laundering"] == 1, "Account.1"])
print("Laundering accounts that are sender-only:", len(laundering_senders & only_sender))
print("Laundering accounts that are receiver-only:", len((laundering_senders | laundering_receivers) & only_receiver))