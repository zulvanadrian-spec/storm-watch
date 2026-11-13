'''
kode ini mencatat setiap ada sinyal datang
'''


import json, random, sys, time, urllib.request

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
rng = random.Random()


def kirim(path, data):
    req = urllib.request.Request(URL + path, json.dumps(data).encode(), {"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=5).read()


def fase(d):
    d %= 90
    return "tenang" if d < 50 else ("badai" if d < 80 else "mereda")


def event_petir():
    return {"signal_metric": rng.gauss(-35, 6), "duration_ms": rng.gammavariate(2.0, 0.8),
            "rise_time_us": max(2, rng.gauss(15, 5)), "jumlah_pulsa": rng.randint(1, 4)}


def event_noise():
    return {"signal_metric": rng.gauss(-45, 7), "duration_ms": rng.gammavariate(3.0, 2.5),
            "rise_time_us": max(2, rng.gauss(40, 15)), "jumlah_pulsa": rng.randint(1, 11)}


OFFSET = float(sys.argv[2]) if len(sys.argv) > 2 else 0
mulai, cuaca_terakhir = time.time() - OFFSET, 0
print("Simulator jalan ->", URL, "(Ctrl+C untuk berhenti)")
while True:
    try:
        f = fase(time.time() - mulai)
        if rng.random() < 0.25:
            kirim("/event", event_noise())
        if f == "badai":
            for _ in range(rng.randint(1, 4)):
                kirim("/event", event_petir())
        elif f == "mereda" and rng.random() < 0.4:
            kirim("/event", event_petir())
        if time.time() - cuaca_terakhir > 5:
            hujan = {"tenang": rng.uniform(0, 0.3), "badai": rng.uniform(8, 30), "mereda": rng.uniform(1, 6)}[f]
            kirim("/cuaca", {"curah_hujan_mm": round(hujan, 2), "kelembapan_persen": round(rng.uniform(60, 95), 1)})
            cuaca_terakhir = time.time()
        time.sleep(0.5)
    except KeyboardInterrupt:
        break
    except Exception as e:
        print("Gagal kirim (server nyala?):", e)
        time.sleep(2)