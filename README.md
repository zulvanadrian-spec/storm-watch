# UBP Storm Watch: Analitik & Dashboard Live

Sistem kecil untuk menerima sinyal radio (RF event kandidat) dari alat, menebak "petir / bukan petir" pakai model ML, lalu menampilkannya di dashboard yang update otomatis.

> **Status:** masih memakai **data dummy/simulasi**. Istilah yang dipakai adalah *RF event kandidat*, bukan "petir terdeteksi". Sistem ini **bukan alat peringatan dini resmi** dan **tidak memprediksi hujan**.

## Alur

```
alat / simulator --POST /event, /cuaca--> server (FastAPI) --model ML--> ringkasan --GET /ringkasan--> dashboard (HTML/CSS/JS)
```

- **Server** (`server.py`): menerima data, menebak pakai model, meringkas per interval 10 detik.
- **Model** (`latih_model.py`): Decision Tree, dilatih dari 4 ciri sinyal.
- **Dashboard** (`dashboard_live.html`): HTML + CSS + JavaScript biasa dengan Chart.js, mengambil ringkasan tiap 3 detik.
- **Simulator** (`dev/simulator.py`): pura-pura jadi alat, dipakai selama hardware belum siap.

## Struktur folder

```
new_jarkom_fp/
├── .gitignore
├── README.md
└── storm_live/
    ├── server.py
    ├── latih_model.py
    ├── dashboard_live.html
    ├── data/                    # tempat data asli dari hardware (nanti)
    └── dev/                     # khusus pengembangan
        ├── 01_buat_data_dummy.py
        ├── simulator.py
        ├── event_dummy.csv
        └── cuaca_dummy.csv
```

File berikut **tidak ikut di Git** dan dibuat ulang saat dijalankan: `model_petir.joblib`, `event_live.csv`, `__pycache__/`.

## Cara menjalankan (Windows)

Semua perintah di bawah memakai `py`. Siapkan **2 jendela terminal**.

### 0. Install library (sekali saja)

```
py -m pip install fastapi uvicorn pandas scikit-learn joblib
```

### 1. Siapkan data dan model (sekali saja)

Jika `dev/event_dummy.csv` belum ada, bikin dulu:

```
cd storm_live\dev
py 01_buat_data_dummy.py
cd ..
```

Latih model dari folder `storm_live`:

```
py latih_model.py
```

Harus muncul `OK -> model_petir.joblib`, dan file itu ada di `storm_live/` (sejajar `server.py`).

### 2. Jendela 1: server (dari folder `storm_live`)

```
py -m uvicorn server:app --port 8000
```

Biarkan menyala. Model hanya dimuat saat server start, jadi **restart server setiap kali model dilatih ulang**.

### 3. Jendela 2: simulator (dari folder `storm_live\dev`)

```
py simulator.py http://127.0.0.1:8000 45
```

Angka `45` membuat simulasi mulai dekat fase badai. Siklus simulasi 90 detik: tenang, badai, mereda.

### 4. Buka dashboard

Buka **http://127.0.0.1:8000** di browser. Jangan double-click file HTML-nya, karena dashboard butuh server.

Dokumentasi API interaktif ada di **http://127.0.0.1:8000/docs**.

## Kontrak data (untuk tim hardware)

Alat mengirim JSON lewat HTTP ke server. Ganti `127.0.0.1` dengan IP laptop yang menjalankan server (satu jaringan WiFi), dan jalankan server dengan `--host 0.0.0.0` agar bisa diakses dari perangkat lain.

### `POST /event`: satu sinyal

| Kolom | Tipe | Wajib | Keterangan |
|---|---|---|---|
| `signal_metric` | float | ya | Kekuatan sinyal (dB relatif) |
| `duration_ms` | float | ya | Durasi sinyal (milidetik) |
| `rise_time_us` | float | ya | Waktu naik sinyal (mikrodetik) |
| `jumlah_pulsa` | int | ya | Jumlah pulsa |
| `timestamp_utc` | float | tidak | Epoch detik (UTC). Jika kosong, dipakai waktu server menerima |
| `confidence` | float | tidak | Keyakinan detektor |
| `station_id` | string | tidak | Default `UBP-01` |

Contoh:

```json
{"signal_metric": -35.2, "duration_ms": 1.4, "rise_time_us": 15.0, "jumlah_pulsa": 2}
```

Balasan: `{"label": 1}` (1 = kandidat petir, 0 = bukan, `null` = model belum dimuat).

### `POST /cuaca`: satu bacaan cuaca

| Kolom | Tipe | Wajib |
|---|---|---|
| `curah_hujan_mm` | float | ya |
| `kelembapan_persen` | float | tidak |
| `suhu_c` | float | tidak |

### `GET /ringkasan`

Dipakai dashboard. Parameter: `bucket` (detik per interval, default 10) dan `n` (jumlah interval, default 60). Mengembalikan deret ringkasan, cuaca terbaru, dan 8 sinyal terakhir.

### Mencoba dari PowerShell

```
Invoke-RestMethod -Uri http://127.0.0.1:8000/event -Method Post -ContentType "application/json" -Body '{"signal_metric":-30,"duration_ms":1.5,"rise_time_us":12,"jumlah_pulsa":2}'
```

### Mencoba dari Python

```python
import json, urllib.request

data = {"signal_metric": -30, "duration_ms": 1.5, "rise_time_us": 12, "jumlah_pulsa": 2}
req = urllib.request.Request("http://127.0.0.1:8000/event", json.dumps(data).encode(),
                             {"Content-Type": "application/json"})
print(urllib.request.urlopen(req).read())
```

## Saat data hardware asli sudah ada

1. Pastikan kolom dan satuan sesuai kontrak di atas (zona waktu: UTC).
2. Simpan data asli di `storm_live/data/`.
3. Data asli **biasanya tidak punya kolom `is_petir`** (label). Ada dua pilihan:
   - **Ada label valid** (dari sumber pembanding resmi): ubah path di `latih_model.py`, latih ulang, lalu restart server.
   - **Tidak ada label**: jangan klaim klasifikasi. Pakai pendekatan tanpa label (z-score, Isolation Forest, K-Means) dan cuaca sebagai pembanding.
4. Jangan menyetel model supaya bagus di data dummy. Latih ulang dari nol memakai data asli.

## Pemecahan masalah

| Gejala | Penyebab / solusi |
|---|---|
| Kolom "Tebakan model" berisi `-` | Model belum dimuat. Pastikan `model_petir.joblib` ada di `storm_live/`, lalu **restart server**. Cek `/ringkasan` dan lihat `"model_siap"` bernilai `true` |
| `Could not import module "server"` | Server dijalankan dari folder yang salah. Jalankan dari `storm_live` |
| `ModuleNotFoundError` | Library belum terpasang. Ulangi langkah 0 |
| `No such file ... event_dummy.csv` | Buat ulang dengan `py 01_buat_data_dummy.py` di folder `dev`, atau periksa path di `latih_model.py` |
| Dashboard menampilkan kotak merah | Server belum menyala, atau dashboard dibuka tanpa lewat `http://127.0.0.1:8000` |
| Simulator menulis `Gagal kirim` | Server mati atau port berbeda |

## Keterbatasan

- Data masih dummy. Akurasi tinggi (sekitar 98%) terjadi karena data sengaja dibuat mudah dibedakan, bukan hasil nyata.
- Sinyal radio bisa berasal dari sumber non-petir (motor listrik, pagar listrik, dan sebagainya).
- Korelasi sinyal dengan hujan bukan bukti sebab-akibat.
- Cuaca tidak dipakai sebagai fitur model. Ia hanya pembanding, untuk menghindari kebocoran data.
- Bukan alat peringatan dini resmi dan tidak memprediksi hujan.
