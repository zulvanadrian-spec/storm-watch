import numpy as np
import pandas as pd

rng = np.random.default_rng(42)

HARI = 30
mulai = pd.Timestamp("2026-10-01 00:00:00")

# 1) CUACA PER JAM
jam_index = pd.date_range(mulai, periods=HARI * 24, freq="h")
cuaca = pd.DataFrame({"timestamp_utc": jam_index})
cuaca["jam_wib"] = (cuaca["timestamp_utc"].dt.hour + 7) % 24

hari_badai = rng.choice(HARI, size=9, replace=False)
badai = np.zeros(len(cuaca), dtype=bool)
for h in hari_badai:
    mulai_badai = h * 24 + int(rng.integers(6, 9))
    lama = int(rng.integers(2, 5))
    badai[mulai_badai:mulai_badai + lama] = True

cuaca["badai"] = badai
base_hujan = rng.exponential(0.05, len(cuaca))
cuaca["curah_hujan_mm"] = np.where(
    badai, rng.uniform(5, 30, len(cuaca)), base_hujan
).round(2)
cuaca["kelembapan_persen"] = np.where(
    badai, rng.uniform(85, 98, len(cuaca)), rng.uniform(55, 85, len(cuaca))
).round(1)
cuaca["tekanan_hpa"] = np.where(
    badai, rng.normal(1004, 1.5, len(cuaca)), rng.normal(1010, 1.5, len(cuaca))
).round(1)
cuaca["suhu_c"] = np.where(
    badai, rng.normal(27, 1, len(cuaca)), rng.normal(31, 2, len(cuaca))
).round(1)

def kondisi(r):
    if r["badai"]:
        return "badai"
    if r["curah_hujan_mm"] > 0.5:
        return "hujan"
    if r["kelembapan_persen"] > 78:
        return "berawan"
    return "cerah"

cuaca["kondisi"] = cuaca.apply(kondisi, axis=1)
cuaca = cuaca.drop(columns=["badai"])

# 2) EVENT RF
baris = []
for _, r in cuaca[cuaca["kondisi"] == "badai"].iterrows():
    n = int(rng.integers(15, 60))
    for _ in range(n):
        ts = r["timestamp_utc"] + pd.Timedelta(seconds=float(rng.uniform(0, 3600)))
        baris.append({
            "timestamp_utc": ts,
            "signal_metric": rng.normal(-35, 6),
            "duration_ms": rng.gamma(2.0, 0.8),
            "rise_time_us": max(2, rng.normal(15, 5)),
            "jumlah_pulsa": int(rng.integers(1, 5)),
            "is_petir": 1,
        })

bobot_jam = np.r_[np.full(6, 0.02), np.full(12, 0.06), np.full(6, 0.03)]
bobot_jam = bobot_jam / bobot_jam.sum()
for _ in range(900):
    jam = int(rng.choice(24, p=bobot_jam))
    hari = int(rng.integers(0, HARI))
    ts = mulai + pd.Timedelta(days=hari, hours=jam, seconds=float(rng.uniform(0, 3600)))
    baris.append({
        "timestamp_utc": ts,
        "signal_metric": rng.normal(-45, 7),
        "duration_ms": rng.gamma(3.0, 2.5),
        "rise_time_us": max(2, rng.normal(40, 15)),
        "jumlah_pulsa": int(rng.integers(1, 12)),
        "is_petir": 0,
    })

ev = pd.DataFrame(baris).sort_values("timestamp_utc").reset_index(drop=True)
ev["timestamp_utc"] = ev["timestamp_utc"].dt.floor("s")

ev.insert(0, "event_id", [f"EVT-2026-{i+1:05d}" for i in range(len(ev))])
ev["frequency_hz"] = 28_000_000
ev["detector_version"] = "v1.0"
conf = 1 / (1 + np.exp(-(ev["signal_metric"] + 42) / 6)) + rng.normal(0, 0.08, len(ev))
ev["confidence"] = conf.clip(0, 1).round(3)
ev["station_id"] = "UBP-01"
ev["weather_ref"] = ev["timestamp_utc"].dt.floor("h").dt.strftime("%Y-%m-%dT%H")

for c in ["signal_metric", "duration_ms", "rise_time_us"]:
    ev[c] = ev[c].round(2)

ev = ev[[
    "event_id", "timestamp_utc", "frequency_hz", "signal_metric", "duration_ms",
    "rise_time_us", "jumlah_pulsa", "detector_version", "confidence",
    "station_id", "weather_ref", "is_petir",
]]

cuaca.to_csv("cuaca_dummy.csv", index=False)
ev.to_csv("event_dummy.csv", index=False)

print(f"event_dummy.csv : {len(ev)} baris ({ev['is_petir'].sum()} petir, {(ev['is_petir']==0).sum()} noise)")
print(f"cuaca_dummy.csv : {len(cuaca)} baris")
print(cuaca['kondisi'].value_counts().to_string())