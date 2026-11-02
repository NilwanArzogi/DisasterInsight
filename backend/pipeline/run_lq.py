"""Jalankan perhitungan LQ pada data nyata 2018-2023, validasi, dan uji sensitivitas.

Keluaran:
- data/output/lq_2018_2023.csv             (hasil utama, tidak masuk Git)
- data/output/lq_sensitivitas_2018_2023.csv (perbandingan dua satuan hitung, tidak masuk Git)
- docs/laporan_lq.md                        (ringkasan, masuk Git)

Penggunaan (dari folder backend, dengan .venv aktif):
    python pipeline/run_lq.py
"""
import sys

import pandas as pd
from check_consistency import CLEAN_CSV, cari_file_agregat
from load_aggregate import load_aggregate
from load_events import ROOT
from lq import JENIS_FOKUS, hitung_lq

TAHUN_AWAL, TAHUN_AKHIR = 2018, 2023
OUTPUT_DIR = ROOT / "data" / "output"
DOCS_DIR = ROOT / "docs"
KODE_PERIKSA_MANUAL = "3201"  # Bogor
JENIS_PERIKSA_MANUAL = "TANAH LONGSOR"


def validasi(hasil: pd.DataFrame, kejadian: pd.DataFrame) -> list:
    """Pemeriksaan independen: dihitung ulang tanpa memakai fungsi LQ."""
    periode = kejadian[kejadian["tahun"].between(TAHUN_AWAL, TAHUN_AKHIR)]
    cek = []

    for jenis in JENIS_FOKUS:
        langsung = int((periode["jenis_bencana"] == jenis).sum())
        dari_hasil = int(hasil.loc[hasil["jenis_bencana"] == jenis, "e_ik"].sum())
        cek.append((f"Jumlah {jenis} = jumlah baris data bersih", langsung == dari_hasil, f"{dari_hasil} vs {langsung}"))

    per_wilayah = hasil.drop_duplicates("kode_kabupaten")
    total_semua = int(per_wilayah["e_i_semua"].sum())
    nasional = hasil["e_nasional_semua"].iloc[0]
    cek.append(("E(nasional,semua) = jumlah E(i,semua)", total_semua == nasional, f"{total_semua} vs {nasional}"))

    for jenis in JENIS_FOKUS:
        sub = hasil[(hasil["jenis_bencana"] == jenis) & (hasil["status"] != "tidak_dapat_dihitung")]
        rata = (sub["lq"] * sub["e_i_semua"]).sum() / sub["e_i_semua"].sum()
        cek.append((f"Rata-rata LQ berbobot {jenis} = 1", abs(rata - 1) < 1e-9, f"{rata:.12f}"))

    cek.append(("Tidak ada LQ negatif", bool((hasil["lq"].dropna() >= 0).all()), ""))
    cek.append(("Tidak ada pembilang melebihi penyebut", bool((hasil["e_ik"] <= hasil["e_i_semua"]).all()), ""))
    return cek


def sensitivitas(utama: pd.DataFrame, alternatif: pd.DataFrame) -> pd.DataFrame:
    kunci = ["kode_kabupaten", "jenis_bencana"]
    gabung = utama.merge(alternatif, on=kunci, suffixes=("_baris", "_unik"))
    gabung["ganti_kategori"] = gabung["kategori_baris"] != gabung["kategori_unik"]
    gabung["lintas_batas_1"] = (gabung["lq_baris"] > 1) != (gabung["lq_unik"] > 1)
    return gabung[
        kunci + ["nama_kabupaten_baris", "e_ik_baris", "e_ik_unik", "lq_baris", "lq_unik",
                 "kategori_baris", "kategori_unik", "ganti_kategori", "lintas_batas_1"]
    ]


def ringkas_sensitivitas(sens: pd.DataFrame) -> pd.DataFrame:
    baris = []
    for jenis, grup in sens.groupby("jenis_bencana"):
        ok = grup.dropna(subset=["lq_baris", "lq_unik"])
        baris.append({
            "jenis": jenis,
            "kabupaten_dibandingkan": len(ok),
            # korelasi Spearman = korelasi Pearson pada peringkat (tanpa perlu scipy)
            "korelasi_peringkat": round(ok["lq_baris"].rank().corr(ok["lq_unik"].rank()), 3),
            "ganti_kategori": int(grup["ganti_kategori"].sum()),
            "lintas_batas_1": int(grup["lintas_batas_1"].sum()),
        })
    return pd.DataFrame(baris)


def cetak_periksa_manual(hasil: pd.DataFrame) -> str:
    b = hasil[(hasil["kode_kabupaten"] == KODE_PERIKSA_MANUAL) & (hasil["jenis_bencana"] == JENIS_PERIKSA_MANUAL)]
    if b.empty:
        return f"Kode {KODE_PERIKSA_MANUAL} tidak ada di hasil."
    r = b.iloc[0]
    return (
        f"{r['nama_kabupaten']} ({r['kode_kabupaten']}), {r['jenis_bencana']}\n"
        f"  E(i,k)={r['e_ik']}  E(i,semua)={r['e_i_semua']}  "
        f"E(nasional,k)={r['e_nasional_k']}  E(nasional,semua)={r['e_nasional_semua']}\n"
        f"  LQ = ({r['e_ik']}/{r['e_i_semua']}) / ({r['e_nasional_k']}/{r['e_nasional_semua']}) = {r['lq']:.4f}  [{r['kategori']}]"
    )


if __name__ == "__main__":
    agregat = load_aggregate(cari_file_agregat(sys.argv[1:]))
    kejadian = pd.read_csv(CLEAN_CSV, dtype={"kode_kabupaten": str}, parse_dates=["tanggal"])

    utama = hitung_lq(kejadian, agregat, TAHUN_AWAL, TAHUN_AKHIR, satuan="baris")
    alternatif = hitung_lq(kejadian, agregat, TAHUN_AWAL, TAHUN_AKHIR, satuan="kab_hari_jenis")
    sens = sensitivitas(utama, alternatif)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    utama.to_csv(OUTPUT_DIR / "lq_2018_2023.csv", index=False)
    sens.to_csv(OUTPUT_DIR / "lq_sensitivitas_2018_2023.csv", index=False)

    cek = validasi(utama, kejadian)
    status = pd.crosstab(utama["jenis_bencana"], utama["status"])
    kategori = pd.crosstab(utama["jenis_bencana"], utama["kategori"])
    sedikit = utama.groupby("jenis_bencana")["data_sedikit"].sum().rename("kabupaten_data_sedikit")
    ringkas = ringkas_sensitivitas(sens)

    teks = ["# Laporan Hasil LQ (2018-2023)", "", "Dibuat otomatis oleh `backend/pipeline/run_lq.py`.", "",
            "## Validasi independen", "```"]
    teks += [f"[{'LULUS' if ok else 'GAGAL'}] {nama} ({rinci})" if rinci else f"[{'LULUS' if ok else 'GAGAL'}] {nama}"
             for nama, ok, rinci in cek]
    teks += ["```", "", "## Status per jenis bencana", "```", status.to_string(), "```", "",
             "## Kategori per jenis bencana", "```", kategori.to_string(), "```", "",
             "## Kabupaten dengan data sedikit (total kejadian < 10)", "```", sedikit.to_string(), "```", "",
             "## Sensitivitas satuan hitung (baris vs kombinasi unik kabupaten-tanggal-jenis)", "```",
             ringkas.to_string(index=False), "```", "",
             "## Pemeriksaan manual satu kabupaten", "```", cetak_periksa_manual(utama), "```", ""]
    laporan = "\n".join(teks)
    (DOCS_DIR / "laporan_lq.md").write_text(laporan, encoding="utf-8")
    print(laporan)

    for jenis in JENIS_FOKUS:
        sub = utama[(utama["jenis_bencana"] == jenis) & (~utama["data_sedikit"]) & (utama["status"] == "ok")]
        print(f"\n10 LQ tertinggi {jenis} (kabupaten dengan total kejadian >= 10):")
        print(sub.nlargest(10, "lq")[["kode_kabupaten", "nama_kabupaten", "e_ik", "e_i_semua", "lq"]].to_string(index=False))