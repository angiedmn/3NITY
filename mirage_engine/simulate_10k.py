import numpy as np
import time
from sklearn.metrics import classification_report
from pathlib import Path
from xgboost import XGBClassifier

# Distinct from train_model.py's seed (42) — this data is still drawn from
# the SAME distributions as training (same np.random.randint/uniform
# ranges), so a strong score here mostly confirms the model learned those
# ranges, not that it generalizes to real, messier, out-of-distribution
# companies. Treat this as an in-sample self-consistency check, not a
# genuine held-out validation.
np.random.seed(7)

num_shells = 2_000_000
num_real = 98_000_000

print(f"🔍 Generating {num_shells + num_real:,} companies with FX Variance... ")
print("⚠️  NOTE: these are drawn from the same distributions used to train the")
print("   model, so this measures in-sample self-consistency, not real-world")
print("   generalization. Validate against real/held-out labeled data too.")
start_gen = time.time()

# 6 columns now! FX variance is symmetric — matches the retrained model's
# training distribution in train_model.py (loss AND gain both count as
# irregular for shells; real businesses vary in a narrow band either side
# of zero).
shell_fx_loss = np.random.uniform(0.10, 0.50, num_shells // 2)
shell_fx_gain = np.random.uniform(-0.50, -0.10, num_shells - num_shells // 2)
shell_fx = np.concatenate((shell_fx_loss, shell_fx_gain))
np.random.shuffle(shell_fx)

shell_data = np.column_stack((
    np.random.randint(500, 5000, num_shells),
    np.random.randint(0, 180, num_shells),
    np.zeros(num_shells),
    np.random.uniform(0.0, 0.2, num_shells),
    np.random.uniform(6.0, 10.0, num_shells),
    shell_fx
))

real_data = np.column_stack((
    np.random.randint(1, 50, num_real),
    np.random.randint(365, 5000, num_real),
    np.ones(num_real),
    np.random.uniform(0.4, 1.0, num_real),
    np.random.uniform(0.0, 4.0, num_real),
    np.random.uniform(-0.03, 0.05, num_real) # Standard FX variance, either direction
))

X_test = np.vstack((shell_data, real_data))
y_true = np.concatenate((np.zeros(num_shells), np.ones(num_real)))

print(f"✅ Data generated in {time.time() - start_gen:.2f} seconds!")

model_path = Path("app/engine/models/mirage_classifier.json")
try:
    clf = XGBClassifier()
    clf.load_model(str(model_path))
    print("✅ XGBoost Model loaded successfully!\n")
except Exception:
    print("❌ Model not found! Run train_model.py first.")
    exit()

print("🚀 Pushing 100 MILLION companies through the Mirage Engine...")
start_time = time.time()
y_pred = clf.predict(X_test)
end_time = time.time()

print("-" * 50)
print(f"⏱️ Processed 100,000,000 companies in {end_time - start_time:.4f} seconds!")
print("-" * 50)

shells_caught = sum(y_pred[:num_shells] == 0)
shells_missed = num_shells - shells_caught

print(f"Target: Find {num_shells:,} Shell Companies")
print(f"Caught: {shells_caught:,}")
print(f"Missed: {shells_missed:,}\n")

print("Detailed Classification Report:")
print(classification_report(y_true, y_pred, target_names=["Shell Company (0)", "Real Business (1)"]))