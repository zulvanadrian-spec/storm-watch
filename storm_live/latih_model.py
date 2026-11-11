"""
latih_model.py - Latih model SEKALI, simpan ke model_petir.joblib
Jalanin: py latih_model.py
"""
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import classification_report

FITUR = ["signal_metric", "duration_ms", "rise_time_us", "jumlah_pulsa"]

ev = pd.read_csv("dev/event_dummy.csv")
X_latih, X_uji, y_latih, y_uji = train_test_split(
    ev[FITUR], ev["is_petir"], test_size=0.25, random_state=42, stratify=ev["is_petir"]
)
model = DecisionTreeClassifier(max_depth=3, random_state=42).fit(X_latih, y_latih)
print(classification_report(y_uji, model.predict(X_uji), target_names=["bukan petir", "petir"]))
joblib.dump({"model": model, "fitur": FITUR}, "model_petir.joblib")
print("OK -> model_petir.joblib")