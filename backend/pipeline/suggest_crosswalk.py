"""Usulan tabel padanan kode kabupaten (terutama Papua).

Untuk setiap kode di data kejadian yang tidak ada di file agregat, cari
kabupaten di file agregat dengan nama yang sama atau mirip. Hasilnya hanya
USULAN: harus diperiksa manual sebelum dipakai.

Penggunaan (dari folder backend, dengan .venv aktif):
    python pipeline/suggest_crosswalk.py
    python pipeline/suggest_crosswalk.py "..\\data\\raw\\NAMA_FILE_AGREGAT.xlsx"
"""
import sys
from difflib import get_close_matches

import pandas as pd
from check_consistency import CLEAN_CSV, cari_file_agregat
from load_aggregate import load_aggregate


def usulan(kejadian: pd.DataFrame, agregat: pd.DataFrame) -> pd.DataFrame:
    kode_agregat = set(agregat["kode_kabupaten"])
    luar = kejadian[~kejadian["kode_kabupaten"].isin(kode_agregat)]
    daftar_agregat = agregat.drop_duplicates("kode_kabupaten").set_index("nama_kabupaten")["kode_kabupaten"]

    baris = []
    for (kode, nama, provinsi), grup in luar.groupby(["kode_kabupaten", "nama_kabupaten", "provinsi"]):
        if nama in daftar_agregat.index:
            kandidat, status = [nama], "nama sama"
        else:
            kandidat = get_close_matches(nama, list(daftar_agregat.index), n=3, cutoff=0.8)
            status = "nama mirip" if kandidat else "TIDAK DITEMUKAN"
        baris.append({
            "kode_lama": kode,
            "nama_kejadian": nama,
            "provinsi_kejadian": provinsi,
            "kejadian": len(grup),
            "status": status,
            "kandidat_kode_baru": ", ".join(daftar_agregat[k] for k in kandidat),
            "nama_di_agregat": ", ".join(kandidat),
        })
    return pd.DataFrame(baris).sort_values("kejadian", ascending=False)


if __name__ == "__main__":
    agregat = load_aggregate(cari_file_agregat(sys.argv[1:]))
    kejadian = pd.read_csv(CLEAN_CSV, dtype={"kode_kabupaten": str})
    hasil = usulan(kejadian, agregat)
    if hasil.empty:
        print("Semua kode di data kejadian sudah ada di file agregat.")
    else:
        pd.set_option("display.width", 200)
        print(hasil.to_string(index=False))