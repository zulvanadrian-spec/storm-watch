'''
program yang akan menerima catatan mengirim ke AI models
lalu meringkasnya
'''

import csv, os, threading, time
from collections import deque
from typing import Optional

import joblib, pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="UBP Storm Watch Live")

# Izin CORS buat frontend (dev). Nanti batasi origin-nya kalau sudah deploy.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
KUNCI = threading.Lock()
EVENTS = deque(maxlen=20000)
CUACA = deque(maxlen=5000)
BASE = os.path.dirname(os.path.abspath(__file__))   # semua path nempel ke lokasi server.py
CSV_LIVE = os.path.join(BASE, "event_live.csv")
MODEL_PATH = os.path.join(BASE, "model_petir.joblib")

PAKET = joblib.load(MODEL_PATH) if os.path.exists(MODEL_PATH) else None


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
    tekanan_hpa: Optional[float] = None


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
                       "rise": e.rise_time_us, "pulsa": e.jumlah_pulsa, "label": label, "sid": e.station_id})
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
        CUACA.append({"t": time.time(), "hujan": c.curah_hujan_mm, "lembap": c.kelembapan_persen,
                      "suhu": c.suhu_c, "tekanan": c.tekanan_hpa})
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
        petir_all = [e for e in EVENTS if e["label"] == 1]
        total_petir, petir_terbaru = len(petir_all), petir_all[-10:][::-1]
        cuaca_riwayat = list(CUACA)[-30:]
        terakhir_t = EVENTS[-1]["t"] if EVENTS else None
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
    perangkat = []                      # dibangun dari event masuk (belum ada registry perangkat)
    if terakhir_t is not None:
        online = now - terakhir_t < 30
        perangkat = [{"device_id": "UBP-01", "device_name": "RTL-SDR Station UBP-01", "device_type": "RTL-SDR + antena",
                      "connection_status": "online" if online else "offline",
                      "last_seen": time.strftime("%H:%M:%S", time.localtime(terakhir_t)),
                      "sensor_status": "Menerima sinyal" if online else "Tidak ada sinyal"}]

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
        "total_petir": total_petir, "cuaca_riwayat": cuaca_riwayat, "perangkat": perangkat,
        "petir_terbaru": [{"t": e["t"], "sig": round(e["sig"], 1), "dur": round(e["dur"], 2), "rise": round(e["rise"], 1)} for e in petir_terbaru],
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


# ==========================================
# ROUTING FRONTEND (folder ../frontend di root repo; cadangan: ./dashboard)
# ==========================================
FRONTEND_DIR = next((p for p in (os.path.abspath(os.path.join(BASE, "..", "frontend")), os.path.join(BASE, "dashboard"))
                     if os.path.exists(os.path.join(p, "index.html"))), None)
print("\n" + "=" * 50)
print("Frontend ditemukan di:", FRONTEND_DIR or "TIDAK KETEMU (cek folder frontend/index.html)")
print("=" * 50 + "\n")

if FRONTEND_DIR and os.path.isdir(os.path.join(FRONTEND_DIR, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")


@app.get("/")
def dashboard():
    if FRONTEND_DIR:
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
    return FileResponse(os.path.join(BASE, "dashboard_live.html"))


@app.get("/backup")
def dashboard_cadangan():
    return FileResponse(os.path.join(BASE, "dashboard_live.html"))