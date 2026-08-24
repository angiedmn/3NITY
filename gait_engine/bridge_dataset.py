import pandas as pd
import numpy as np

#load and column map
def enrich_ibm_with_gait(ibm_csv_path: str, output_csv_path: str):
    print(f"Loading IBM dataset from {ibm_csv_path}...")
    df_transactions = pd.read_csv(ibm_csv_path)
    
    sender_col = 'Account' if 'Account' in df_transactions.columns else 'Sender_account'
    label_col = 'Is Laundering' if 'Is Laundering' in df_transactions.columns else 'Is_Laundering'
    
    if sender_col not in df_transactions.columns or label_col not in df_transactions.columns:
        raise ValueError(f"Could not find the required columns. Available columns are: {df_transactions.columns.tolist()}")

    print("Mapping laundering networks...")
    illicit_accounts = df_transactions[df_transactions[label_col] == 1][sender_col].unique()
    all_accounts = df_transactions[sender_col].unique()
    
    df_accounts = pd.DataFrame({'account_id': all_accounts})
    df_accounts['is_illicit'] = df_accounts['account_id'].isin(illicit_accounts).astype(int)
    
    df_accounts['label'] = np.where(df_accounts['is_illicit'] == 1, 'coerced_mule', 'human')
    
    total_accounts = len(df_accounts)
    illicit_count = df_accounts['is_illicit'].sum()
    print(f"Found {total_accounts} total accounts. {illicit_count} flagged as illicit.")

    print("Injecting synthetic Gait telemetry...")
    np.random.seed(42) 
    
    # 1. Clipboard Usage 
    df_accounts['clipboard_paste_count'] = np.where(
        df_accounts['is_illicit'] == 1,
        np.random.randint(4, 15, total_accounts), #mules/bots (high value)
        np.random.randint(0, 3, total_accounts)   #normal human
    )
    
    # 2. App Switching 
    df_accounts['app_switch_count'] = np.where(
        df_accounts['is_illicit'] == 1,
        np.random.randint(4, 10, total_accounts), #mules/bots (high value)
        np.random.randint(0, 3, total_accounts)
    )

    # 3. Keystroke Mean (MISSING COLUMN ADDED) - Mules type slower/hesitant
    df_accounts['keystroke_interval_mean_ms'] = np.where(
        df_accounts['is_illicit'] == 1,
        np.random.uniform(300.0, 500.0, total_accounts), #mules/bots (high value)
        np.random.uniform(100.0, 200.0, total_accounts)   #normal human
    )
    
    # 4. Keystroke Consistency 
    df_accounts['keystroke_interval_std_ms'] = np.where(
        df_accounts['is_illicit'] == 1,
        np.random.uniform(100.0, 200.0, total_accounts), #mules/bots (high value)
        np.random.uniform(20.0, 60.0, total_accounts)   #normal human
    )
    
    # 5. Session Dwell Time 
    df_accounts['session_dwell_time_sec'] = np.where(
        df_accounts['is_illicit'] == 1,
        np.random.uniform(1.0, 4.9, total_accounts), #mules/bots (high value)
        np.random.uniform(30.0, 300.0, total_accounts)   #normal human
    )

    # 6. Touch Pressure Variance
    df_accounts['touch_pressure_var'] = np.where(
        df_accounts['is_illicit'] == 1,
        np.random.uniform(0.1, 0.8, total_accounts), #mules/bots (high value)
        np.random.uniform(0.01, 0.05, total_accounts)   #normal human
    )

    # 7. Gyro Tilt Variance
    df_accounts['gyro_tilt_var'] = np.where(
        df_accounts['is_illicit'] == 1,
        np.random.uniform(0.1, 0.9, total_accounts), #mules/bots (high value)
        np.random.uniform(0.01, 0.05, total_accounts)   #normal human
    )
    
    # 8. Flight Time 
    df_accounts['flight_time_mean_ms'] = np.where(
        df_accounts['is_illicit'] == 1,
        np.random.uniform(150.0, 300.0, total_accounts), #mules/bots (high value)
        np.random.uniform(50.0, 100.0, total_accounts)   #normal human
    )
    
    # 9. Mouse Trajectory 
    df_accounts['mouse_curve_index'] = np.where(
        df_accounts['is_illicit'] == 1,
        np.random.uniform(0.01, 0.09, total_accounts), #mules/bots (high value)
        np.random.uniform(1.0, 2.5, total_accounts)   #normal human
    )
    
    # 10. Time of Day Risk 
    df_accounts['time_of_day_risk'] = np.where(
        df_accounts['is_illicit'] == 1,
        np.random.uniform(0.8, 1.0, total_accounts), #mules/bots (high value)
        np.random.uniform(0.1, 0.5, total_accounts)   #normal human
    )
    
    # Save the Enriched Dataset
    df_accounts.to_csv(output_csv_path, index=False)
    print(f"Success! Enriched telemetry saved to {output_csv_path}")
    
    return df_accounts

if __name__ == "__main__":
    input_file = "HI-Small_Trans.csv" 
    output_file = "gait_telemetry_synthetic.csv"
    
    try:
        enriched_df = enrich_ibm_with_gait(input_file, output_file)
        print("\nSample of Enriched Illicit Accounts:")
        print(enriched_df[enriched_df['is_illicit'] == 1].head())
    except FileNotFoundError:
        print(f"Error: Could not find '{input_file}'.")
    except pd.errors.EmptyDataError:
        print(f"Error: '{input_file}' is empty. The download likely failed. Please redownload it.")