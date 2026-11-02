"""Perhitungan Location Quotient (LQ) kejadian bencana per kabupaten/kota.

LQ(i,k) = [E(i,k) / E(i,semua)] / [E(nasional,k) / E(nasional,semua)]

LQ adalah ukuran konsentrasi relatif jumlah kejadian yang DILAPORKAN. LQ tidak
mempertimbangkan penduduk, luas wilayah, paparan, kerentanan, maupun kapasitas
penanggulangan, dan bukan probabilitas, prediksi, atau peta rawan resmi.
"""
import math

import pandas as pd

JENIS_FOKUS = ["BANJIR", "TANAH LONGSOR", "KEBAKARAN HUTAN DAN LAHAN"]
SATUAN_VALID = ("baris", "kab_hari_jenis")
AMBANG_MINIMUM = 10  # kabupaten dengan total kejadian di bawah ini diberi peringatan


def lq_satu(e_ik, e_i_semua, e_nasional_k, e_nasional_semua):
    """Hitung satu nilai LQ. Kembalikan (lq, status).

    status:
    - "ok"                    : LQ dihitung, kejadian jenis ini ada
    - "tidak_ada_laporan"     : kejadian jenis ini nol (LQ = 0.0), penyebut valid
    - "tidak_dapat_dihitung"  : salah satu penyebut nol, LQ = NaN
    """
    nilai = (e_ik, e_i_semua, e_nasional_k, e_nasional_semua)
    if any(pd.isna(v) or v < 0 for v in nilai):
        raise ValueError(f"Jumlah kejadian harus bilangan tidak negatif: {nilai}")
    if e_ik > e_i_semua:
        raise ValueError(
            f"E(i,k)={e_ik} tidak boleh melebihi E(i,semua)={e_i_semua}"
        )
    if e_i_semua == 0 or e_nasional_semua == 0 or e_nasional_k == 0:
        return math.nan, "tidak_dapat_dihitung"
    lq = (e_ik / e_i_semua) / (e_nasional_k / e_nasional_semua)
    return lq, ("tidak_ada_laporan" if e_ik == 0 else "ok")


def kategori_lq(lq, status):
    """Kategori untuk legenda peta. Bukan tingkat risiko."""
    if status == "tidak_dapat_dihitung":
        return "tidak dapat dihitung"
    if status == "tidak_ada_laporan":
        return "tidak ada laporan"
    if math.isclose(lq, 1.0, abs_tol=1e-9):
        return "LQ = 1"
    return "LQ > 1" if lq > 1 else "LQ < 1"


def _terapkan_satuan(kejadian, satuan):
    if satuan not in SATUAN_VALID:
        raise ValueError(f"satuan harus salah satu dari {SATUAN_VALID}, bukan {satuan!r}")
    if satuan == "kab_hari_jenis":
        return kejadian.drop_duplicates(["kode_kabupaten", "tanggal", "jenis_bencana"])
    return kejadian


def hitung_lq(
    kejadian,
    agregat,
    tahun_awal=2018,
    tahun_akhir=2023,
    jenis=None,
    satuan="baris",
    ambang_minimum=AMBANG_MINIMUM,
):
    """Hitung LQ semua kabupaten dan jenis bencana untuk satu periode.

    kejadian: kolom kode_kabupaten, tanggal, tahun, jenis_bencana
    agregat : kolom kode_kabupaten, nama_kabupaten, tahun, jumlah_semua_jenis
    E(i,semua) = jumlah per tahun dari max(agregat, jumlah jenis fokus), lalu dijumlahkan.
    """
    jenis = list(jenis) if jenis is not None else JENIS_FOKUS

    k = kejadian[
        kejadian["tahun"].between(tahun_awal, tahun_akhir)
        & kejadian["jenis_bencana"].isin(jenis)
    ]
    k = _terapkan_satuan(k, satuan)
    ag = agregat[agregat["tahun"].between(tahun_awal, tahun_akhir)]

    # penyebut per kabupaten-tahun: agregat tidak boleh lebih kecil dari jumlah jenis fokus
    fokus = k.groupby(["kode_kabupaten", "tahun"]).size().rename("jenis_fokus").reset_index()
    kt = ag[["kode_kabupaten", "tahun", "jumlah_semua_jenis"]].merge(
        fokus, on=["kode_kabupaten", "tahun"], how="outer"
    )
    kt[["jumlah_semua_jenis", "jenis_fokus"]] = kt[["jumlah_semua_jenis", "jenis_fokus"]].fillna(0)
    kt["penyebut"] = kt[["jumlah_semua_jenis", "jenis_fokus"]].max(axis=1)
    e_i_semua = kt.groupby("kode_kabupaten")["penyebut"].sum()

    e_ik = k.groupby(["kode_kabupaten", "jenis_bencana"]).size()
    e_nasional_k = k.groupby("jenis_bencana").size().reindex(jenis, fill_value=0)
    e_nasional_semua = e_i_semua.sum()

    nama = (
        ag.drop_duplicates("kode_kabupaten").set_index("kode_kabupaten")["nama_kabupaten"]
        if len(ag)
        else pd.Series(dtype=str)
    )

    baris = []
    for kode in e_i_semua.index:
        for j in jenis:
            e = int(e_ik.get((kode, j), 0))
            semua = int(e_i_semua[kode])
            semua_efektif = max(semua, e)  # pengaman; tidak berpengaruh bila penyebut sudah max
            lq, status = lq_satu(e, semua_efektif, int(e_nasional_k[j]), int(e_nasional_semua))
            baris.append(
                {
                    "kode_kabupaten": kode,
                    "nama_kabupaten": nama.get(kode, ""),
                    "jenis_bencana": j,
                    "e_ik": e,
                    "e_i_semua": semua_efektif,
                    "e_nasional_k": int(e_nasional_k[j]),
                    "e_nasional_semua": int(e_nasional_semua),
                    "lq": lq,
                    "status": status,
                    "kategori": kategori_lq(lq, status),
                    "data_sedikit": semua_efektif < ambang_minimum,
                }
            )
    kolom = [
        "kode_kabupaten", "nama_kabupaten", "jenis_bencana", "e_ik", "e_i_semua",
        "e_nasional_k", "e_nasional_semua", "lq", "status", "kategori", "data_sedikit",
    ]
    return pd.DataFrame(baris, columns=kolom)