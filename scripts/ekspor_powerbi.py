"""Ekspor model bintang untuk Power BI -> D:\\DisasterInsight\\data\\powerbi\\*.csv"""
import csv, sqlite3, sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "disasterinsight.db"
LQ = ROOT / "data" / "output" / "lq_2018_2023.csv"
OUT = ROOT / "data" / "powerbi"
OUT.mkdir(parents=True, exist_ok=True)

BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
         "Agustus", "September", "Oktober", "November", "Desember"]


def tulis(nama, kolom, rows):
    rows = list(rows)
    with open(OUT / nama, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(kolom)
        w.writerows(rows)
    print(f"{nama}: {len(rows)} baris")


c = sqlite3.connect(DB)

jenis = [r[0] for r in c.execute(
    "select distinct jenis_bencana from kejadian order by jenis_bencana")]
jkey = {j: i + 1 for i, j in enumerate(jenis)}
tulis("dim_jenis_bencana.csv", ["jenis_key", "jenis_bencana"],
      [(jkey[j], j) for j in jenis])

tulis("dim_wilayah.csv", ["kode_kabupaten", "nama_kabupaten", "kode_provinsi", "provinsi"],
      c.execute("select kode, nama, kode_provinsi, provinsi from wilayah order by kode"))

tahun_min, tahun_max = c.execute("select min(tahun), max(tahun) from kejadian").fetchone()
tulis("dim_tahun.csv", ["tahun"], [(t,) for t in range(tahun_min, tahun_max + 1)])

hari, d = [], date(tahun_min, 1, 1)
while d <= date(tahun_max, 12, 31):
    hari.append((int(d.strftime("%Y%m%d")), d.isoformat(), d.year,
                 (d.month - 1) // 3 + 1, d.month, BULAN[d.month - 1]))
    d += timedelta(days=1)
tulis("dim_tanggal.csv",
      ["tanggal_key", "tanggal", "tahun", "kuartal", "bulan_no", "nama_bulan"], hari)

contoh = c.execute("select tanggal from kejadian limit 1").fetchone()[0]
try:
    date.fromisoformat(str(contoh)[:10])
except ValueError:
    sys.exit(f"Format tanggal tak terduga: {contoh!r}. Kirim contoh ini ke Claude.")

def baris_kejadian():
    for id_, kode, tgl, jns, ganda in c.execute(
            "select id, kode_kabupaten, tanggal, jenis_bencana, ganda_kab_tgl_jenis from kejadian"):
        yield (id_, kode, int(str(tgl)[:10].replace("-", "")), jkey[jns], ganda)

tulis("fact_kejadian.csv",
      ["id", "kode_kabupaten", "tanggal_key", "jenis_key", "ganda_kab_tgl_jenis"],
      baris_kejadian())

tulis("fact_agregat.csv",
      ["kode_kabupaten", "tahun", "jumlah_semua_jenis", "tiga_jenis", "penyebut"],
      c.execute("""
        select a.kode_kabupaten, a.tahun, a.jumlah_semua_jenis,
               coalesce(k.n, 0) as tiga_jenis,
               max(a.jumlah_semua_jenis, coalesce(k.n, 0)) as penyebut
        from agregat a
        left join (select kode_kabupaten, tahun, count(*) as n
                   from kejadian group by 1, 2) k
          on k.kode_kabupaten = a.kode_kabupaten and k.tahun = a.tahun
        order by 1, 2"""))
tot = c.execute("""
    select sum(a.jumlah_semua_jenis),
           sum(max(a.jumlah_semua_jenis, coalesce(k.n, 0)))
    from agregat a
    left join (select kode_kabupaten, tahun, count(*) as n
               from kejadian group by 1, 2) k
      on k.kode_kabupaten = a.kode_kabupaten and k.tahun = a.tahun""").fetchone()
print(f"Total agregat mentah: {tot[0]} | total penyebut: {tot[1]}  (harus 26577 dan 26671)")

with open(LQ, encoding="utf-8-sig", newline="") as f:
    rd = csv.DictReader(f)
    kolom = list(rd.fieldnames) + ["jenis_key"]
    baris = []
    for r in rd:
        r["kode_kabupaten"] = str(r["kode_kabupaten"]).strip()
        r["jenis_key"] = jkey[r["jenis_bencana"]]
        baris.append([r[k] for k in kolom])
tulis("fact_lq.csv", kolom, baris)

n = c.execute("select count(*) from kejadian where kode_kabupaten in ('7412','9208','9506','9508')").fetchone()[0]
print(f"\nKejadian untuk 7412/9208/9506/9508 di database: {n}")
print(f"Tersimpan di: {OUT}")