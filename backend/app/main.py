import logging
from typing import List, Literal, Optional

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Path, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import schemas
from app.config import settings
from app.db import buat_engine, muat_data
from app.store import DataStore

log = logging.getLogger("disasterinsight")

JenisQ = Literal["BANJIR", "TANAH LONGSOR", "KEBAKARAN HUTAN DAN LAHAN"]
KategoriQ = Literal["LQ < 1", "LQ = 1", "LQ > 1", "tidak ada laporan", "tidak dapat dihitung"]
KATEGORI = ["LQ < 1", "LQ = 1", "LQ > 1", "tidak ada laporan", "tidak dapat dihitung"]
KODE_PROVINSI_POLA = r"^\d{2}$"


def get_store(request: Request) -> DataStore:
    return request.app.state.store


def periode(
    store: DataStore = Depends(get_store),
    tahun_awal: Optional[int] = Query(None, description="Tahun awal periode"),
    tahun_akhir: Optional[int] = Query(None, description="Tahun akhir periode"),
):
    awal = store.tahun_min if tahun_awal is None else tahun_awal
    akhir = store.tahun_max if tahun_akhir is None else tahun_akhir
    for t in (awal, akhir):
        if not store.tahun_min <= t <= store.tahun_max:
            raise HTTPException(422, f"Tahun harus antara {store.tahun_min} dan {store.tahun_max}.")
    if awal > akhir:
        raise HTTPException(422, "tahun_awal tidak boleh lebih besar dari tahun_akhir.")
    return awal, akhir


def cek_provinsi(store: DataStore, provinsi: Optional[str]):
    if provinsi is not None and provinsi not in set(store.provinsi["kode_provinsi"]):
        raise HTTPException(422, "Kode provinsi tidak dikenal.")


def _ke_catatan(df: pd.DataFrame) -> list:
    """DataFrame -> daftar dict yang aman untuk JSON (NaN menjadi None)."""
    return df.astype(object).where(df.notna(), None).to_dict("records")


def _baris_lq(store: DataStore, df: pd.DataFrame) -> list:
    kolom = ["kode_kabupaten", "nama_kabupaten", "provinsi", "jenis_bencana", "e_ik", "e_i_semua",
             "e_nasional_k", "e_nasional_semua", "lq", "status", "kategori", "data_sedikit"]
    return _ke_catatan(df[kolom])


def _sumber(store: DataStore) -> list:
    s = store.sumber.copy()
    s["diimpor_pada"] = s["diimpor_pada"].astype(str)
    return _ke_catatan(s[["nama", "url", "keterangan", "diimpor_pada"]])


def _tren(k: pd.DataFrame, awal: int, akhir: int, jenis: List[str]) -> list:
    hitung = k.groupby(["tahun", "jenis_bencana"]).size()
    baris = []
    for tahun in range(awal, akhir + 1):
        for j in jenis:
            baris.append({"tahun": tahun, "jenis_bencana": j, "jumlah": int(hitung.get((tahun, j), 0))})
    return baris


def create_app(engine=None) -> FastAPI:
    engine = engine or buat_engine()
    app = FastAPI(
        title="DisasterInsight Indonesia API",
        description="Analisis Location Quotient (LQ) kejadian banjir, tanah longsor, dan kebakaran hutan dan lahan per kabupaten/kota.",
        version="0.1.0",
    )
    app.state.store = DataStore(muat_data(engine))

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins,
        allow_methods=["GET"],
        allow_headers=["Content-Type"],
    )

    @app.exception_handler(Exception)
    async def kesalahan_server(request: Request, exc: Exception):
        log.exception("Kesalahan tak terduga pada %s", request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Terjadi kesalahan pada server."})

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/opsi", response_model=schemas.ResponOpsi)
    def opsi(store: DataStore = Depends(get_store)):
        return {
            "tahun_min": store.tahun_min,
            "tahun_max": store.tahun_max,
            "jenis_bencana": store.jenis,
            "provinsi": [{"kode": r.kode_provinsi, "nama": r.provinsi} for r in store.provinsi.itertuples()],
            "kategori": KATEGORI,
            "ambang_data_sedikit": store.ambang_minimum,
            "sumber": _sumber(store),
            "catatan_metode": schemas.CATATAN_METODE,
        }

    @app.get("/api/lq", response_model=schemas.ResponLQ)
    def daftar_lq(
        store: DataStore = Depends(get_store),
        per: tuple = Depends(periode),
        jenis: Optional[JenisQ] = None,
        provinsi: Optional[str] = Query(None, pattern=KODE_PROVINSI_POLA, description="Kode provinsi 2 digit"),
        cari: Optional[str] = Query(None, max_length=50, description="Bagian nama kabupaten/kota"),
        kategori: Optional[KategoriQ] = None,
        urut: Literal["lq", "e_ik", "e_i_semua", "nama"] = "lq",
        arah: Literal["asc", "desc"] = "desc",
        halaman: int = Query(1, ge=1),
        ukuran: int = Query(50, ge=1, le=2000),
    ):
        cek_provinsi(store, provinsi)
        hasil = store.lq(*per) 
        if jenis:
            hasil = hasil[hasil["jenis_bencana"] == jenis]
        if provinsi:
            hasil = hasil[hasil["kode_provinsi"] == provinsi]
        if cari and cari.strip():
            hasil = hasil[hasil["nama_kabupaten"].str.contains(cari.strip().upper(), regex=False)]
        if kategori:
            hasil = hasil[hasil["kategori"] == kategori]
        kolom_urut = "nama_kabupaten" if urut == "nama" else urut
        hasil = hasil.sort_values(kolom_urut, ascending=(arah == "asc"), na_position="last", kind="stable")
        total = len(hasil)
        halaman_ini = hasil.iloc[(halaman - 1) * ukuran: halaman * ukuran]
        return {
            "meta": {
                "periode": {"awal": per[0], "akhir": per[1]},
                "jumlah_total": total,
                "halaman": halaman,
                "ukuran": ukuran,
                "ambang_data_sedikit": store.ambang_minimum,
                "catatan_metode": schemas.CATATAN_METODE,
            },
            "data": _baris_lq(store, halaman_ini),
        }

    @app.get("/api/ringkasan", response_model=schemas.ResponRingkasan)
    def ringkasan(
        store: DataStore = Depends(get_store),
        per: tuple = Depends(periode),
        jenis: Optional[JenisQ] = None,
        provinsi: Optional[str] = Query(None, pattern=KODE_PROVINSI_POLA),
    ):
        cek_provinsi(store, provinsi)
        awal, akhir = per
        k = store.kejadian[store.kejadian["tahun"].between(awal, akhir)]
        if provinsi:
            k = k[k["kode_kabupaten"].str[:2] == provinsi]
        if jenis:
            k = k[k["jenis_bencana"] == jenis]
        jenis_tampil = [jenis] if jenis else store.jenis

        per_jenis = [{"jenis_bencana": j, "jumlah": int((k["jenis_bencana"] == j).sum())} for j in jenis_tampil]
        teratas = (
            k.groupby("kode_kabupaten").size().rename("jumlah").reset_index()
            .sort_values(["jumlah", "kode_kabupaten"], ascending=[False, True]).head(10)
        )
        wilayah_tertinggi = [
            {"kode_kabupaten": r.kode_kabupaten,
             "nama_kabupaten": store.nama_wilayah.get(r.kode_kabupaten, ""),
             "provinsi": store.nama_provinsi.get(r.kode_kabupaten, ""),
             "jumlah": int(r.jumlah)}
            for r in teratas.itertuples()
        ]

        lq = store.lq(awal, akhir)
        if provinsi:
            lq = lq[lq["kode_provinsi"] == provinsi]
        ringkasan_lq = []
        for j in jenis_tampil:
            hitung = lq[lq["jenis_bencana"] == j]["kategori"].value_counts()
            ringkasan_lq.append({"jenis_bencana": j, "kategori": {c: int(hitung.get(c, 0)) for c in KATEGORI}})

        return {
            "periode": {"awal": awal, "akhir": akhir},
            "total_kejadian": int(len(k)),
            "per_jenis": per_jenis,
            "wilayah_tertinggi": wilayah_tertinggi,
            "tren": _tren(k, awal, akhir, jenis_tampil),
            "ringkasan_lq": ringkasan_lq,
            "catatan_metode": schemas.CATATAN_METODE,
        }

    @app.get("/api/wilayah/{kode}", response_model=schemas.ResponWilayah)
    def detail_wilayah(
        kode: str = Path(..., pattern=r"^\d{4}$", description="Kode kabupaten/kota 4 digit"),
        store: DataStore = Depends(get_store),
        per: tuple = Depends(periode),
    ):
        if kode not in store.nama_wilayah:
            raise HTTPException(404, "Wilayah tidak ditemukan.")
        awal, akhir = per
        lq = store.lq(awal, akhir)
        lq = lq[lq["kode_kabupaten"] == kode]
        k = store.kejadian[(store.kejadian["kode_kabupaten"] == kode) & store.kejadian["tahun"].between(awal, akhir)]
        ag = store.agregat[(store.agregat["kode_kabupaten"] == kode) & store.agregat["tahun"].between(awal, akhir)]
        return {
            "kode_kabupaten": kode,
            "nama_kabupaten": store.nama_wilayah[kode],
            "provinsi": store.nama_provinsi[kode],
            "periode": {"awal": awal, "akhir": akhir},
            "lq": _baris_lq(store, lq),
            "tren": _tren(k, awal, akhir, store.jenis),
            "agregat_per_tahun": [
                {"tahun": int(r.tahun), "semua_jenis": int(r.jumlah_semua_jenis)}
                for r in ag.sort_values("tahun").itertuples()
            ],
            "sumber": _sumber(store),
            "catatan_metode": schemas.CATATAN_METODE,
        }

    return app
