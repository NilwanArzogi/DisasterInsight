import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # agar paket `app` dapat diimpor

import pandas as pd
from app.config import ROOT
from app.db import bangun_database, buat_engine, database_berisi
from check_consistency import CLEAN_CSV, cari_file_agregat
from load_aggregate import load_aggregate

PROVINSI_CSV = ROOT / "backend" / "reference" / "provinsi.csv"


def siapkan_tabel(kejadian: pd.DataFrame, agregat_panjang: pd.DataFrame, provinsi: pd.DataFrame) -> dict:
    nama = agregat_panjang.drop_duplicates("kode_kabupaten")[["kode_kabupaten", "nama_kabupaten"]]
    tambahan = kejadian.drop_duplicates("kode_kabupaten")[["kode_kabupaten", "nama_kabupaten"]]
    tambahan = tambahan[~tambahan["kode_kabupaten"].isin(nama["kode_kabupaten"])]
    wilayah = pd.concat([nama, tambahan], ignore_index=True)
    wilayah["kode_provinsi"] = wilayah["kode_kabupaten"].str[:2]
    wilayah = wilayah.merge(
        provinsi.rename(columns={"kode": "kode_provinsi", "nama": "provinsi"}), on="kode_provinsi", how="left"
    )
    tanpa_provinsi = wilayah[wilayah["provinsi"].isna()]
    if len(tanpa_provinsi):
        raise ValueError(
            + ", ".join(sorted(tanpa_provinsi["kode_provinsi"].unique()))
        )
    wilayah = wilayah.rename(columns={"kode_kabupaten": "kode", "nama_kabupaten": "nama"})[
        ["kode", "nama", "kode_provinsi", "provinsi"]
    ]

    agregat = agregat_panjang[["kode_kabupaten", "tahun", "jumlah_semua_jenis"]].copy()
    agregat["jumlah_semua_jenis"] = agregat["jumlah_semua_jenis"].astype(int)
    return {"wilayah": wilayah, "agregat": agregat}


def tabel_sumber(jumlah_kejadian: int, jumlah_agregat: int) -> pd.DataFrame:
    sekarang = datetime.now(timezone.utc).replace(tzinfo=None)
    return pd.DataFrame([
        {
            "nama": "Data kejadian bencana (DIBI BNPB)",
            "url": "https://gis.bnpb.go.id/databencana/tabel/pencarian.php",
            "keterangan": "Banjir, tanah longsor, dan kebakaran hutan dan lahan, 2018-2023, setelah pembersihan",
            "diimpor_pada": sekarang,
            "jumlah_baris": jumlah_kejadian,
        },
        {
            "nama": "Jumlah kejadian bencana menurut kabupaten (Portal Satu Data Bencana Indonesia)",
            "url": "https://data.bnpb.go.id/dataset/data-bencana-indonesia",
            "keterangan": "Total semua jenis bencana per kabupaten per tahun, dipakai sebagai penyebut LQ",
            "diimpor_pada": sekarang,
            "jumlah_baris": jumlah_agregat,
        },
    ])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bangun database SQLite DisasterInsight")
    parser.add_argument("agregat", nargs="?", help="path file agregat (opsional)")
    parser.add_argument("--timpa", action="store_true", help="hapus dan bangun ulang database yang sudah berisi")
    args = parser.parse_args()

    engine = buat_engine()
    if database_berisi(engine) and not args.timpa:
        sys.exit(
            f"Database sudah berisi data ({engine.url}).\n"
            "Data lama tidak ditimpa tanpa konfirmasi. Jika memang ingin membangun ulang, "
            "jalankan lagi dengan opsi --timpa."
        )

    agregat_panjang = load_aggregate(cari_file_agregat([args.agregat] if args.agregat else []))
    kejadian = pd.read_csv(CLEAN_CSV, dtype={"kode_kabupaten": str}, parse_dates=["tanggal"])
    provinsi = pd.read_csv(PROVINSI_CSV, dtype=str)

    tabel = siapkan_tabel(kejadian, agregat_panjang, provinsi)
    jumlah = bangun_database(
        engine,
        wilayah_df=tabel["wilayah"],
        kejadian_df=kejadian,
        agregat_df=tabel["agregat"],
        sumber_df=tabel_sumber(len(kejadian), len(tabel["agregat"])),
    )
    print("Database dibangun:", engine.url)
    for nama, n in jumlah.items():
        print(f"  {nama}: {n} baris")
