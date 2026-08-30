from dotenv import load_dotenv
load_dotenv()

# FIXED: was "dataset/HI-Small_Trans.csv" — every other engine
# (gait_engine/bridge_dataset.py, gateway/seed_dataset.py) expects the
# CSV at the repo root. Keep this in sync with those.
DATA_PATH = "HI-Small_Trans.csv"