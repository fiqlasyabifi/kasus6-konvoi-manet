# olah_hasil.py - menghitung PDR, delay, overhead AODV, dan RERR dari hasil OMNeT++
import glob, io, re, shutil, subprocess
import pandas as pd

# ---- PENGATURAN ----
SCA_CSV = "hasil_mentah.csv"   # opp_scavetool export -F CSV-R -o hasil_mentah.csv results/*.sca
PCAP_GLOB = "results/Konvoi-v*-r*-car*.pcap"
TSHARK = shutil.which("tshark") or r"C:\Program Files\Wireshark\tshark.exe"
WINDOW_S = 280                 # lama pengiriman data: detik 10-290
T_95 = 2.262                   # nilai t (95%, df = 10 - 1) untuk interval kepercayaan


def baca_csv(path):
    """Baca CSV-R dengan aman.
    Sebagian baris (histogram, config) ikut dibungkus tanda kutip satu baris penuh,
    sehingga pandas membacanya sebagai satu kolom saja. Kutip luar itu dibuang dulu."""
    baris = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            s = line.rstrip("\r\n")
            if len(s) > 1 and s.startswith('"') and s.endswith('"') and s.count(",") > 3:
                s = s[1:-1].replace('""', '"')
            baris.append(s)
    return pd.read_csv(io.StringIO("\n".join(baris)), low_memory=False)


# ---- 1. Statistik aplikasi dari file .sca ----
df = baca_csv(SCA_CSV)
attrs = df[df["type"].isin(["itervar", "runattr"])]
runinfo = attrs.pivot_table(index="run", columns="attrname", values="attrvalue", aggfunc="first")
runinfo = runinfo[["speed", "repetition"]].astype(int)

sc = df[df["type"] == "scalar"].copy()
sc["value"] = pd.to_numeric(sc["value"], errors="coerce")

# hanya modul aplikasi (app[...]); modul udp juga mencatat paket AODV (port 654), jadi jangan ikut dihitung
is_app = sc["module"].str.contains(r"\.app\[", regex=True)
sent = sc[(sc["name"] == "packetSent:count") & is_app].groupby("run")["value"].sum()
recv = sc[(sc["name"] == "packetReceived:count") & is_app].groupby("run")["value"].sum()

# delay dari histogram endToEndDelay di UdpSink (tetap tersimpan di .sca walau vector-recording = false)
h = df[(df["type"] == "histogram") & (df["name"] == "endToEndDelay:histogram")].copy()
for c in ["count", "mean"]:
    h[c] = pd.to_numeric(h[c], errors="coerce")
h["w"] = h["count"] * h["mean"]
g = h.groupby("run")[["w", "count"]].sum()
delay_ms = g["w"] / g["count"] * 1000

app = runinfo.copy()
app["sent"] = sent
app["received"] = recv
app["pdr_pct"] = recv / sent * 100
app["delay_ms"] = delay_ms
app = app.reset_index(drop=True)

# cek silang: jumlah sampel delay harus sama dengan paket diterima
if not (g["count"].reindex(runinfo.index).values == recv.reindex(runinfo.index).values).all():
    print("PERINGATAN: jumlah sampel delay != paket diterima. Cek hasil_mentah.csv")

# ---- 2. Paket AODV dari file .pcap (pakai tshark) ----
TYPES = {"1": "rreq", "2": "rrep", "3": "rerr"}
rows = []
for f in sorted(glob.glob(PCAP_GLOB)):
    m = re.search(r"-v(\d+)-r(\d+)-car(\d+)\.pcap$", f)
    speed, rep, car = map(int, m.groups())
    out = subprocess.run(
        [TSHARK, "-r", f, "-Y", "aodv && wlan.fc.retry == 0", "-T", "fields", "-e", "aodv.type"],
        capture_output=True, text=True, check=True).stdout.split()
    row = {"speed": speed, "repetition": rep, "rreq": 0, "rrep": 0, "rerr": 0}
    for t in out:
        if t in TYPES:
            row[TYPES[t]] += 1
    rows.append(row)
aodv = pd.DataFrame(rows).groupby(["speed", "repetition"], as_index=False).sum()

# ---- 3. Gabungkan & hitung metrik per run ----
per_run = app.merge(aodv, on=["speed", "repetition"], how="left")
per_run["aodv_total"] = per_run[["rreq", "rrep", "rerr"]].sum(axis=1)
per_run["nrl"] = per_run["aodv_total"] / per_run["received"]
per_run["rerr_per_min"] = per_run["rerr"] / (WINDOW_S / 60)
per_run["rreq_per_min"] = per_run["rreq"] / (WINDOW_S / 60)
per_run = per_run.sort_values(["speed", "repetition"])
per_run.to_csv("per_run.csv", index=False)

# ---- 4. Ringkasan per kecepatan: rata-rata dan CI 95% ----
metrics = ["pdr_pct", "delay_ms", "aodv_total", "nrl", "rerr_per_min", "rreq_per_min"]
summ = per_run.groupby("speed")[metrics].agg(["mean", "std", "count"])
out = pd.DataFrame(index=summ.index)
for mt in metrics:
    out[mt + "_mean"] = summ[(mt, "mean")]
    out[mt + "_ci95"] = T_95 * summ[(mt, "std")] / summ[(mt, "count")] ** 0.5
out.round(4).to_csv("ringkasan.csv")

print("--- Data per run ---")
print(per_run.round(2).to_string(index=False))
print("\n--- Ringkasan per kecepatan ---")
print(out.round(3).T.to_string())
