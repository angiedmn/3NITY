import os
import pandas as pd
import numpy as np
import psycopg2
from pgvector.psycopg2 import register_vector
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get("SUPABASE_DB_URL")
if not DB_URL:
    raise ValueError("Missing SUPABASE_DB_URL in environment or .env file.")

# Fixed paths pointing directly inside the gait_engine folder
KAGGLE_CSV = "gait_engine/HI-Small_Trans.csv"
SYNTHETIC_GAIT_CSV = "gait_engine/gait_telemetry_synthetic.csv"
SAMPLE_SIZE = 1000  

def seed_database():
    print("Connecting to Supabase via Pooler...")
    conn = psycopg2.connect(DB_URL)
    register_vector(conn)
    cur = conn.cursor()

    # ==========================================
    # 1. SEED TEMPO LEDGER (From Kaggle Dataset)
    # ==========================================
    print(f"Reading Kaggle Dataset ({KAGGLE_CSV})...")
    cur.execute("DELETE FROM tempo_ledger;")
    try:
        df_kaggle = pd.read_csv(KAGGLE_CSV, nrows=SAMPLE_SIZE)
        
        sender_col = 'From Bank' if 'From Bank' in df_kaggle.columns else 'Account'
        receiver_col = 'To Bank' if 'To Bank' in df_kaggle.columns else 'Account.1'
        amount_col = 'Amount Received' if 'Amount Received' in df_kaggle.columns else 'Amount_Received'
        
        tempo_rows = []
        for index, row in df_kaggle.iterrows():
            txn_id = f"KAGGLE_{index}"
            timestamp = datetime.now(timezone.utc)
            sender = str(row.get(sender_col, f"UNKNOWN_{index}"))
            receiver = str(row.get(receiver_col, f"UNKNOWN_{index}"))
            amount = float(row.get(amount_col, 100.0))
            
            tempo_rows.append((txn_id, sender, receiver, amount, timestamp))
            
        cur.executemany(
            "INSERT INTO tempo_ledger (transaction_id, sender_account, receiver_account, amount_usd, timestamp) VALUES (%s, %s, %s, %s, %s)",
            tempo_rows
        )
        print(f"✅ Injected {len(tempo_rows)} real transactions into Tempo Ledger.")
    except Exception as e:
        print(f"⚠️ Failed to load Kaggle data: {e}")

    # ==========================================
    # 2. SEED GAIT SESSIONS (From Synthetic Data)
    # ==========================================
    print(f"Reading Synthetic Gait Data ({SYNTHETIC_GAIT_CSV})...")
    cur.execute("DELETE FROM gait_sessions;")
    try:
        df_gait = pd.read_csv(SYNTHETIC_GAIT_CSV, nrows=SAMPLE_SIZE)
        feature_cols = [
            "clipboard_paste_count", "app_switch_count", "keystroke_interval_mean_ms",
            "keystroke_interval_std_ms", "session_dwell_time_sec", "touch_pressure_var",
            "gyro_tilt_var", "flight_time_mean_ms", "mouse_curve_index", "time_of_day_risk"
        ]
        
        gait_rows = []
        for _, row in df_gait.iterrows():
            account_id = str(row['account_id'])
            vector = row[feature_cols].to_numpy(dtype=np.float32).tolist()
            gait_rows.append((account_id, vector))
            
        cur.executemany(
            "INSERT INTO gait_sessions (account_id, embedding) VALUES (%s, %s::vector)",
            gait_rows
        )
        print(f"✅ Injected {len(gait_rows)} biometrics vectors into Gait Sessions.")
    except Exception as e:
        print(f"⚠️ Failed to load synthetic Gait data: {e}")

    # ==========================================
    # 3. SEED MIRAGE REGISTRY (Mock KYB Data)
    # ==========================================
    print("Seeding Mirage Corporate Registry...")
    cur.execute("DELETE FROM mirage_registry;")
    
    # We must ensure the accounts being tested exist in the Mirage registry to prevent 500 errors
    safe_companies = [
        ("ACC_2001", "Acme Global Technologies Inc", "USA", "https://acmeglobal.com", "100 Innovation Way, Boston, MA"),
        ("ACC_2002", "Apex Shell Holdings Ltd", "BVI", "https://apex-temp-portal.xyz", "Suite 404, Offshore Plaza, Tortola"),
        ("ACC_2003", "Nexus Supply Chain LLC", "GBR", "https://nexussupply.co.uk", "12 King Street, London")
    ]
    cur.executemany("""
        INSERT INTO mirage_registry (account_id, company_name, jurisdiction_code, domain_name, registered_address)
        VALUES (%s, %s, %s, %s, %s)
    """, safe_companies)
    print("✅ Injected standard testing entities into Mirage Registry.")

    # Commit and close
    conn.commit()
    cur.close()
    conn.close()
    print("\n🎉 Database fully seeded and ready for 3NITY Gateway!")

if __name__ == "__main__":
    seed_database()