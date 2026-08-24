from collections import defaultdict

def build_account_sequences(df):
    sequences = defaultdict(list)
    for row in df.itertuples(index = False):
        sender_id   = (row.Account,   row.From_Bank)   
        receiver_id = (row.Account_1, row.To_Bank)

        sequences[sender_id].append({"timestamp": row.Timestamp,"role": "sent",})
        sequences[receiver_id].append({"timestamp": row.Timestamp, "role": "received",})

    for events in sequences.values():
        events.sort(key=lambda e: e["timestamp"])

    return sequences;



def is_sorted(events):
    timestamps = [e["timestamp"] for e in events]
    return timestamps == sorted(timestamps)
