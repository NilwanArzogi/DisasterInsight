import re
import sys

import pandas as pd
from check_consistency import CLEAN_CSV, cari_file_agregat
from load_aggregate import load_aggregate


def normalisasi(nama: str) -> str:
    nama = str(nama).upper().strip()
    nama = re.sub(r"^(KABUPATEN|KAB\.?)\s+", "", nama)
    return re.sub(r"[^A-Z0-9]", "", nama)


if __name__ == "__main__":
    agregat = load_aggregate(cari_file_agregat(sys.argv[1:]))
    kejadian = pd.read_csv(CLEAN_CSV, dtype={"kode_kabupaten": str})

    nama_agregat = agregat.drop_duplicates("kode_kabupaten").set_index("kode_kabupaten")["nama_kabupaten"]
    nama_kejadian = (
        kejadian.groupby("kode_kabupaten")["nama_kabupaten"]
        .agg(lambda s: s.value_counts().index[0])
    )
    gabung = pd.concat([nama_kejadian.rename("nama_kejadian"), nama_agregat.rename("nama_agregat")], axis=1, join="inner")
    gabung["sama"] = gabung["nama_kejadian"].map(normalisasi) == gabung["nama_agregat"].map(normalisasi)

    print("Kode yang ada di kedua sumber:", len(gabung))
    print("Nama sama setelah normalisasi:", int(gabung["sama"].sum()))
    beda = gabung[~gabung["sama"]]
    print("Nama berbeda:", len(beda))
    if len(beda):
        pd.set_option("display.width", 200)
        print(beda.drop(columns="sama").to_string())
