"""Memuat file agregat BNPB: jumlah kejadian semua jenis per kabupaten per tahun.

Penggunaan (dari folder backend, dengan .venv aktif):
    python pipeline/load_aggregate.py ..\\data\\raw\\NAMA_FILE.csv
"""
import sys
from pathlib import Path

import pandas as pd

TAHUN_AWAL = 2018
TAHUN_AKHIR = 2023

KOLOM_KODE = "Kode Wilayah Kabupaten / Kota"
KOLOM_NAMA = "Nama Kabupaten/Kota"


def _baca_mentah(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path, encoding="utf-8-sig")
    return pd.read_excel(path)


def _nama_tahun(nama) -> str:
    """Ubah nama kolom seperti 2018.0 atau 2018 menjadi teks '2018'."""
    teks = str(nama).strip()
    return teks[:-2] if teks.endswith(".0") else teks


def load_aggregate(path: Path) -> pd.DataFrame:
    """Kembalikan tabel panjang: kode_kabupaten, nama_kabupaten, tahun, jumlah_semua_jenis."""
    mentah = _baca_mentah(path)
    mentah.columns = [_nama_tahun(c) for c in mentah.columns]

    for kolom in (KOLOM_KODE, KOLOM_NAMA):
        if kolom not in mentah.columns:
            raise ValueError(f"Kolom '{kolom}' tidak ditemukan. Kolom yang ada: {list(mentah.columns)}")

    kolom_tahun = [str(t) for t in range(TAHUN_AWAL, TAHUN_AKHIR + 1)]
    hilang = [t for t in kolom_tahun if t not in mentah.columns]
    if hilang:
        raise ValueError(f"Kolom tahun tidak ditemukan: {hilang}")

    df = mentah[[KOLOM_KODE, KOLOM_NAMA] + kolom_tahun].copy()
    kode = pd.to_numeric(df[KOLOM_KODE], errors="coerce")
    df = df[kode.notna()].copy()
    df["kode_kabupaten"] = kode[kode.notna()].round().astype(int).astype(str).str.zfill(4)
    df["nama_kabupaten"] = df[KOLOM_NAMA].astype(str).str.strip().str.upper()

    panjang = df.melt(
        id_vars=["kode_kabupaten", "nama_kabupaten"],
        value_vars=kolom_tahun,
        var_name="tahun",
        value_name="jumlah_semua_jenis",
    )
    panjang["tahun"] = panjang["tahun"].astype(int)
    panjang["jumlah_semua_jenis"] = pd.to_numeric(panjang["jumlah_semua_jenis"], errors="coerce")
    return panjang


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Penggunaan: python pipeline/load_aggregate.py <path file agregat>")
    data = load_aggregate(Path(sys.argv[1]))
    print("Kabupaten (kode unik):", data["kode_kabupaten"].nunique())
    print("Baris tabel panjang:", len(data))
    print("Pasangan kode+tahun terulang:", data.duplicated(["kode_kabupaten", "tahun"]).sum())
    print("Kode bukan 4 digit:", (~data["kode_kabupaten"].str.fullmatch(r"\d{4}")).sum())
    print("Nilai kosong:", data["jumlah_semua_jenis"].isna().sum())
    print("Nilai negatif:", (data["jumlah_semua_jenis"] < 0).sum())
    print("Total per tahun:")
    print(data.groupby("tahun")["jumlah_semua_jenis"].sum().astype("Int64").to_string())
    print("Contoh:")
    print(data.head(3).to_string())