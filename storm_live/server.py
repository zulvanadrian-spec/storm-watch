'''
program yang akan menerima catatan mengirim ke AI models
lalu meringkasnya
'''

import csv, os, threading, time
from collections import deque
from typing import Optional

import joblib, pandas as pd
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="UBP Storm Watch Live")
KUNCI = threading.Lock()
EVENTS = deque(maxlen=20000)
CUACA = deque(maxlen=5000)
CSV_LIVE = "event_live.csv"

PAKET = joblib.load("model_petir.joblib") if os.path.exists("model_petir.joblib") else None


class Event(BaseModel):
    signal_metric: float
    duration_ms: float
    rise_time_us: float
    jumlah_pulsa: int
    timestamp_utc: Optional[float] = None
    confidence: Optional[float] = None
    station_id: Optional[str] = "UBP-01"


class Cuaca(BaseModel):
    curah_hujan_mm: float
    kelembapan_persen: Optional[float] = None
    suhu_c: Optional[float] = None


def tebak(e: Event):
    if PAKET is None:
        return None
    X = pd.DataFrame([{k: getattr(e, k) for k in PAKET["fitur"]}])[PAKET["fitur"]]
    return int(PAKET["model"].predict(X)[0])


@app.post("/event")
def terima_event(e: Event):
    t = e.timestamp_utc or time.time()
    label = tebak(e)
    with KUNCI:
        EVENTS.append({"t": t, "sig": e.signal_metric, "dur": e.duration_ms,
                       "rise": e.rise_time_us, "pulsa": e.jumlah_pulsa, "label": label})
        baru = not os.path.exists(CSV_LIVE)
        with open(CSV_LIVE, "a", newline="") as f:
            w = csv.writer(f)
            if baru:
                w.writerow(["timestamp_utc", "signal_metric", "duration_ms", "rise_time_us", "jumlah_pulsa", "label_tebakan"])
            w.writerow([round(t, 3), e.signal_metric, e.duration_ms, e.rise_time_us, e.jumlah_pulsa, label])
    return {"label": label}


@app.post("/cuaca")
def terima_cuaca(c: Cuaca):
    with KUNCI:
        CUACA.append({"t": time.time(), "hujan": c.curah_hujan_mm, "lembap": c.kelembapan_persen})
    return {"ok": True}


@app.post("/reset")
def reset():
    with KUNCI:
        EVENTS.clear(); CUACA.clear()
    return {"ok": True}


@app.get("/ringkasan")
def ringkasan(bucket: int = 10, n: int = 60):
    now = time.time()
    awal = (int(now) // bucket) * bucket - (n - 1) * bucket
    with KUNCI:
        ev = [e for e in EVENTS if e["t"] >= awal]
        cu = [c for c in CUACA if c["t"] >= awal - 3600]
        total, terbaru = len(EVENTS), list(EVENTS)[-8:][::-1]
        cuaca_terbaru = CUACA[-1] if CUACA else None
    seri = [{"t": awal + i * bucket, "n_event": 0, "n_petir": 0, "hujan": None, "anomali": False} for i in range(n)]
    for e in ev:
        s = seri[min(n - 1, int((e["t"] - awal) // bucket))]
        s["n_event"] += 1
        s["n_petir"] += 1 if e["label"] == 1 else 0
    terakhir = None
    for s in seri:
        isi = [c["hujan"] for c in cu if s["t"] <= c["t"] < s["t"] + bucket]
        if isi:
            terakhir = sum(isi) / len(isi)
        s["hujan"] = None if terakhir is None else round(terakhir, 2)
    for i, s in enumerate(seri):
        lalu = [x["n_event"] for x in seri[max(0, i - 30):i]]
        if len(lalu) >= 10:
            mu = sum(lalu) / len(lalu)
            sd = (sum((v - mu) ** 2 for v in lalu) / (len(lalu) - 1)) ** 0.5 or 1.0
            s["anomali"] = bool((s["n_event"] - mu) / sd > 3 and s["n_event"] >= 5)

    # =========================================================
    # LOGIKA PREDIKSI / ESTIMASI WAKTU BERIKUTNYA
    # =========================================================
    data_terakhir = seri[-6:]  # Ambil data ~1 menit terakhir
    total_petir_baru = sum(x["n_petir"] for x in data_terakhir)
    list_hujan_baru = [x["hujan"] for x in data_terakhir if x["hujan"] is not None]
    rata_hujan = sum(list_hujan_baru) / len(list_hujan_baru) if list_hujan_baru else 0.0

    # Penentuan status prediksi
    prediksi_petir_next = "POTENSI TINGGI" if total_petir_baru >= 3 else "NORMAL / RENDAH"
    prediksi_cuaca_next = "HUJAN LEBAT" if rata_hujan > 2.0 else ("HUJAN RINGAN" if rata_hujan > 0 else "CERAH / BERAWAN")

    return {
        "info": "DATA SIMULASI. RF event kandidat, bukan deteksi petir resmi.",
        "model_siap": PAKET is not None,
        "bucket_detik": bucket,
        "total_event": total,
        "seri": seri,
        "cuaca_terbaru": cuaca_terbaru,

        "prediksi_next": {
            "waktu_estimasi": "10–30 Menit Ke Depan",
            "petir": prediksi_petir_next,
            "cuaca": prediksi_cuaca_next,
            "ringkasan_prakiraan": f"Dalam 10–30 menit ke depan, kondisi cuaca diperkirakan {prediksi_cuaca_next} dengan potensi petir {prediksi_petir_next}."
        },
        
        "terbaru": [{"jam": time.strftime("%H:%M:%S", time.gmtime(e["t"])), "sig": round(e["sig"], 1),
                     "dur": round(e["dur"], 2), "rise": round(e["rise"], 1), "label": e["label"]} for e in terbaru],
    }


@app.get("/")
def dashboard():
    return FileResponse("dashboard_live.html")