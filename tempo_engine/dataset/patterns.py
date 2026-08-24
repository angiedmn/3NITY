import re
from collections import Counter, defaultdict
from datetime import datetime

pattern_counts = Counter()
attempt_stats = defaultdict(list)  # pattern_type -> list of (n_txns, n_accounts, span_minutes)

current_type = None
current_rows = []

def flush(ptype, rows):
    if not rows or ptype is None:
        return
    timestamps = []
    accounts = set()
    for row in rows:
        # row format: "<timestamp>,<from_bank>,<from_acct>,<to_bank>,<to_acct>,..."
        parts = row.strip()
        fields = parts.split(",")
        ts = datetime.strptime(fields[0].strip(), "%Y/%m/%d %H:%M")
        timestamps.append(ts)
        accounts.add(fields[2])  # from account
        accounts.add(fields[4])  # to account
    span = (max(timestamps) - min(timestamps)).total_seconds() / 60
    attempt_stats[ptype].append((len(rows), len(accounts), span))

with open("HI-Small_Patterns.txt") as f:
    for line in f:
        if line.startswith("BEGIN LAUNDERING ATTEMPT"):
            m = re.search(r"BEGIN LAUNDERING ATTEMPT\s*-\s*([A-Z\-]+)", line)
            current_type = m.group(1).strip() if m else "UNKNOWN"
            pattern_counts[current_type] += 1
            current_rows = []
        elif line.startswith("END LAUNDERING ATTEMPT"):
            flush(current_type, current_rows)
            current_type = None
            current_rows = []
        elif current_type is not None and line.strip():
            current_rows.append(line)

print("Pattern type counts:")
for ptype, count in pattern_counts.most_common():
    print(f"  {ptype}: {count}")

print("\nPer-type stats (avg txns, avg accounts, avg span in minutes):")
for ptype, stats in attempt_stats.items():
    n = len(stats)
    avg_txns = sum(s[0] for s in stats) / n
    avg_accts = sum(s[1] for s in stats) / n
    avg_span = sum(s[2] for s in stats) / n
    print(f"  {ptype}: n_attempts={n}, avg_txns={avg_txns:.1f}, avg_accounts={avg_accts:.1f}, avg_span_min={avg_span:.1f}")