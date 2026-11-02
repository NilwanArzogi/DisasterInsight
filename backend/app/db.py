from pathlib import Path

import pandas as pd
from sqlalchemy import (
    Boolean, Column, Date, DateTime, Integer, MetaData, String, Table,
    create_engine, func, inspect, select,
)
from sqlalchemy.engine import Engine

from app.config import ROOT, settings

metadata = MetaData()

wilayah = Table(
    "wilayah", metadata,
    Column("kode", String(4), primary_key=True),
    Column("nama", String(120), nullable=False),
    Column("kode_provinsi", String(2), nullable=False),
    Column("provinsi", String(80), nullable=False),
)

kejadian = Table(
    "kejadian", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("kode_kabupaten", String(4), nullable=False, index=True),
    Column("tanggal", Date, nullable=False),
    Column("tahun", Integer, nullable=False, index=True),
    Column("jenis_bencana", String(40), nullable=False),
    Column("ganda_kab_tgl_jenis", Boolean, nullable=False, default=False),
)

agregat = Table(
    "agregat", metadata,
    Column("kode_kabupaten", String(4), primary_key=True),
    Column("tahun", Integer, primary_key=True),
    Column("jumlah_semua_jenis", Integer, nullable=False),
)

sumber_data = Table(
    "sumber_data", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("nama", String(200), nullable=False),
    Column("url", String(300), nullable=False),
    Column("keterangan", String(500), nullable=False),
    Column("diimpor_pada", DateTime, nullable=False),
    Column("jumlah_baris", Integer, nullable=False),
)


def _normalisasi_url(url: str) -> str:
    awalan = "sqlite:///"
    if url.startswith(awalan) and url != "sqlite://":
        jalur = Path(url[len(awalan):])
        if str(jalur) != ":memory:" and not jalur.is_absolute():
            jalur = (ROOT / "backend" / jalur).resolve()
        return awalan + jalur.as_posix()
    return url


def buat_engine(url: str = None) -> Engine:
    return create_engine(_normalisasi_url(url or settings.database_url))


def database_berisi(engine: Engine) -> bool:
    if "kejadian" not in inspect(engine).get_table_names():
        return False
    with engine.connect() as koneksi:
        return koneksi.execute(select(func.count()).select_from(kejadian)).scalar_one() > 0


def bangun_database(engine: Engine, *, wilayah_df, kejadian_df, agregat_df, sumber_df) -> dict:
    metadata.drop_all(engine)
    metadata.create_all(engine)

    kej = kejadian_df.copy()
    kej["tanggal"] = pd.to_datetime(kej["tanggal"]).dt.date
    kej["ganda_kab_tgl_jenis"] = kej["ganda_kab_tgl_jenis"].astype(bool)

    with engine.begin() as koneksi:
        koneksi.execute(wilayah.insert(), wilayah_df.to_dict("records"))
        koneksi.execute(
            kejadian.insert(),
            kej[["kode_kabupaten", "tanggal", "tahun", "jenis_bencana", "ganda_kab_tgl_jenis"]].to_dict("records"),
        )
        koneksi.execute(agregat.insert(), agregat_df.to_dict("records"))
        koneksi.execute(sumber_data.insert(), sumber_df.to_dict("records"))
    return {"wilayah": len(wilayah_df), "kejadian": len(kej), "agregat": len(agregat_df), "sumber": len(sumber_df)}


def muat_data(engine: Engine) -> dict:
    if "kejadian" not in inspect(engine).get_table_names():
        raise RuntimeError("Database belum dibuat. Jalankan: python pipeline/build_db.py")
    with engine.connect() as koneksi:
        data = {
            "wilayah": pd.read_sql(select(wilayah), koneksi),
            "kejadian": pd.read_sql(select(kejadian), koneksi),
            "agregat": pd.read_sql(select(agregat), koneksi),
            "sumber": pd.read_sql(select(sumber_data), koneksi),
        }
    if data["kejadian"].empty or data["agregat"].empty:
        raise RuntimeError("Database kosong. Jalankan: python pipeline/build_db.py --timpa")
    data["kejadian"]["tanggal"] = pd.to_datetime(data["kejadian"]["tanggal"])
    return data
