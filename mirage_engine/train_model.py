import numpy as np
import os
from xgboost import XGBClassifier

# Seed numpy too, not just the classifier's random_state below — otherwise
# the *training data itself* differs on every run even though the model's
# own randomness is fixed, making results non-reproducible.
np.random.seed(42)

print("Generating synthetic training data with FX Variance...")

data = []
labels = []

# Generate 1000 Shell Companies (Label: 0)
# FX variance is now symmetric: an under-payment (value LOSS, positive
# variance) and an over-payment (value GAIN, negative variance — classic
# round-tripping / trade-based laundering) are both red flags. Previously
# only the positive/loss direction was ever generated, so the model had
# never seen a negative fx_variance and would silently extrapolate on one
# if worker.py ever produced one from real (received > paid) input.
for i in range(1000):
    if i % 2 == 0:
        fx = np.random.uniform(0.10, 0.50)   # value loss
    else:
        fx = np.random.uniform(-0.50, -0.10)  # value gain / round-tripping
    data.append([
        np.random.randint(500, 5000), 
        np.random.randint(0, 180), 
        0, 
        np.random.uniform(0.0, 0.2), 
        np.random.uniform(6.0, 10.0),
        fx
    ])
    labels.append(0)
    
# Generate 1000 Real Businesses (Label: 1)
for _ in range(1000):
    # 6th feature: Normal FX variance — a narrow band around zero in
    # EITHER direction (small negative covers ordinary rounding/rebates,
    # not just the loss side).
    data.append([
        np.random.randint(1, 50), 
        np.random.randint(365, 5000), 
        1, 
        np.random.uniform(0.4, 1.0), 
        np.random.uniform(0.0, 4.0),
        np.random.uniform(-0.03, 0.05)
    ])
    labels.append(1)

X = np.array(data)
y = np.array(labels)

print("Training hyper-tuned XGBoost Classifier...")

# n_jobs=1: avoids XGBoost's OpenMP multi-threaded code path, which is
# known to segfault (signal 11) rather than raise a catchable exception
# inside resource-constrained Docker containers. See scoring.py for the
# same setting applied at prediction time.
clf = XGBClassifier(n_estimators=300, max_depth=8, learning_rate=0.05, random_state=42, n_jobs=1)
clf.fit(X, y)

os.makedirs("app/engine/models", exist_ok=True)
model_path = "app/engine/models/mirage_classifier.json"
clf.save_model(model_path)

print(f"Success! Model updated with FX Variance feature and saved to {model_path}")