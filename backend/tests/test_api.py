"""Uji API dengan database sementara berisi dataset kecil yang dapat dihitung dengan tangan.

Tahun 2020 (E = jumlah kejadian):
                 banjir  longsor  karhutla | semua jenis
  1101 (Aceh)       6       2        0     |   10
  1102 (Aceh)       1       3        4     |   10
  1201 (Sumut)      3       0        0     |    5
  1301 (Sumbar)     0       0        0     |    0   (penyebut nol)
  nasional         10       5        4     |   25
Tahun 2021: kabupaten 1101 punya 2 banjir, agregat 4.
LQ(1101,banjir,2020) = (6/10)/(10/25) = 1.5 ; LQ(1102,karhutla,2020) = (4/10)/(4/25) = 2.5
"""
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.db import bangun_database, buat_engine, database_berisi, muat_data
from app.main import create_app

B, L, K = "BANJIR", "TANAH LONGSOR", "KEBAKARAN HUTAN DAN LAHAN"


def _kejadian(spesifikasi):
    baris = []
    for (kode, jenis, tahun), jumlah in spesifikasi.items():
        for n in range(jumlah):
            tanggal = pd.Timestamp(f"{tahun}-01-01") + pd.Timedelta(days=n)
            baris.append({"kode_kabupaten": kode, "tanggal": tanggal, "tahun": tahun,
                          "jenis_bencana": jenis, "ganda_kab_tgl_jenis": False})
    return pd.DataFrame(baris)


@pytest.fixture
def engine(tmp_path):
    engine = buat_engine(f"sqlite:///{tmp_path / 'uji.db'}")
    wilayah = pd.DataFrame([
        {"kode": "1101", "nama": "KAB ALFA", "kode_provinsi": "11", "provinsi": "ACEH"},
        {"kode": "1102", "nama": "KAB BETA", "kode_provinsi": "11", "provinsi": "ACEH"},
        {"kode": "1201", "nama": "KOTA GAMMA", "kode_provinsi": "12", "provinsi": "SUMATERA UTARA"},
        {"kode": "1301", "nama": "KAB DELTA", "kode_provinsi": "13", "provinsi": "SUMATERA BARAT"},
    ])
    kejadian = _kejadian({
        ("1101", B, 2020): 6, ("1101", L, 2020): 2, ("1102", B, 2020): 1, ("1102", L, 2020): 3,
        ("1102", K, 2020): 4, ("1201", B, 2020): 3, ("1101", B, 2021): 2,
    })
    agregat = pd.DataFrame([
        {"kode_kabupaten": "1101", "tahun": 2020, "jumlah_semua_jenis": 10},
        {"kode_kabupaten": "1102", "tahun": 2020, "jumlah_semua_jenis": 10},
        {"kode_kabupaten": "1201", "tahun": 2020, "jumlah_semua_jenis": 5},
        {"kode_kabupaten": "1301", "tahun": 2020, "jumlah_semua_jenis": 0},
        {"kode_kabupaten": "1101", "tahun": 2021, "jumlah_semua_jenis": 4},
        {"kode_kabupaten": "1102", "tahun": 2021, "jumlah_semua_jenis": 0},
        {"kode_kabupaten": "1201", "tahun": 2021, "jumlah_semua_jenis": 0},
        {"kode_kabupaten": "1301", "tahun": 2021, "jumlah_semua_jenis": 0},
    ])
    sumber = pd.DataFrame([{
        "nama": "Sumber uji", "url": "https://contoh.test", "keterangan": "uji",
        "diimpor_pada": pd.Timestamp("2026-11-01 08:00:00").to_pydatetime(), "jumlah_baris": 1,
    }])
    bangun_database(engine, wilayah_df=wilayah, kejadian_df=kejadian, agregat_df=agregat, sumber_df=sumber)
    return engine


@pytest.fixture
def klien(engine):
    return TestClient(create_app(engine))


def baris(respons, kode, jenis):
    return next(b for b in respons.json()["data"] if b["kode_kabupaten"] == kode and b["jenis_bencana"] == jenis)


def test_health(klien):
    assert klien.get("/api/health").json() == {"status": "ok"}


def test_opsi(klien):
    j = klien.get("/api/opsi").json()
    assert (j["tahun_min"], j["tahun_max"]) == (2020, 2021)
    assert len(j["jenis_bencana"]) == 3
    assert {"kode": "11", "nama": "ACEH"} in j["provinsi"]
    assert j["sumber"][0]["nama"] == "Sumber uji"
    assert "bukan probabilitas" in j["catatan_metode"]


def test_database_berisi(engine):
    assert database_berisi(engine)
    assert not database_berisi(buat_engine("sqlite://"))


def test_muat_data_gagal_jika_database_belum_dibuat():
    with pytest.raises(RuntimeError):
        muat_data(buat_engine("sqlite://"))


def test_lq_sesuai_hitungan_tangan(klien):
    r = klien.get("/api/lq", params={"tahun_awal": 2020, "tahun_akhir": 2020})
    assert r.status_code == 200
    assert baris(r, "1101", B)["lq"] == pytest.approx(1.5)
    assert baris(r, "1102", K)["lq"] == pytest.approx(2.5)
    assert baris(r, "1102", B)["lq"] == pytest.approx(0.25)
    assert baris(r, "1101", L)["kategori"] == "LQ = 1"
    assert r.json()["meta"]["jumlah_total"] == 12


def test_penyebut_nol_menjadi_null_bukan_nan(klien):
    r = klien.get("/api/lq", params={"tahun_awal": 2020, "tahun_akhir": 2020})
    b = baris(r, "1301", B)
    assert b["lq"] is None
    assert b["status"] == "tidak_dapat_dihitung"
    assert b["kategori"] == "tidak dapat dihitung"


def test_periode_default_mencakup_semua_tahun(klien):
    r = klien.get("/api/lq", params={"jenis": B})
    meta = r.json()["meta"]
    assert (meta["periode"]["awal"], meta["periode"]["akhir"]) == (2020, 2021)
    b = baris(r, "1101", B)
    assert (b["e_ik"], b["e_i_semua"]) == (8, 14)


def test_filter_provinsi_tidak_mengubah_acuan_nasional(klien):
    r = klien.get("/api/lq", params={"tahun_awal": 2020, "tahun_akhir": 2020, "provinsi": "12", "jenis": B})
    data = r.json()["data"]
    assert [d["kode_kabupaten"] for d in data] == ["1201"]
    assert data[0]["lq"] == pytest.approx(1.5)
    assert data[0]["e_nasional_semua"] == 25  


def test_filter_jenis_dan_kategori(klien):
    r = klien.get("/api/lq", params={"tahun_awal": 2020, "tahun_akhir": 2020, "jenis": L, "kategori": "LQ > 1"})
    assert [d["kode_kabupaten"] for d in r.json()["data"]] == ["1102"]


def test_cari_nama_tidak_peka_huruf_besar(klien):
    r = klien.get("/api/lq", params={"cari": "beta", "jenis": B})
    assert [d["kode_kabupaten"] for d in r.json()["data"]] == ["1102"]


def test_cari_dengan_karakter_berbahaya_tidak_error(klien):
    r = klien.get("/api/lq", params={"cari": "'; DROP TABLE kejadian; --"})
    assert r.status_code == 200 and r.json()["data"] == []
    assert klien.get("/api/health").status_code == 200


def test_urutan_dan_halaman(klien):
    params = {"tahun_awal": 2020, "tahun_akhir": 2020, "jenis": K, "urut": "e_ik", "arah": "desc", "ukuran": 1}
    p1 = klien.get("/api/lq", params={**params, "halaman": 1}).json()
    p2 = klien.get("/api/lq", params={**params, "halaman": 2}).json()
    assert p1["data"][0]["kode_kabupaten"] == "1102" 
    assert p1["data"][0]["kode_kabupaten"] != p2["data"][0]["kode_kabupaten"]
    assert p1["meta"]["jumlah_total"] == 4


def test_urut_lq_menaruh_null_di_akhir(klien):
    r = klien.get("/api/lq", params={"tahun_awal": 2020, "tahun_akhir": 2020, "jenis": B, "urut": "lq", "arah": "desc"})
    assert r.json()["data"][-1]["kode_kabupaten"] == "1301"


def test_ringkasan(klien):
    j = klien.get("/api/ringkasan", params={"tahun_awal": 2020, "tahun_akhir": 2020}).json()
    assert j["total_kejadian"] == 19
    assert {p["jenis_bencana"]: p["jumlah"] for p in j["per_jenis"]} == {B: 10, L: 5, K: 4}
    assert j["wilayah_tertinggi"][0]["jumlah"] == 8
    assert len(j["tren"]) == 3  
    banjir = next(r for r in j["ringkasan_lq"] if r["jenis_bencana"] == B)
    assert banjir["kategori"]["tidak dapat dihitung"] == 1


def test_ringkasan_filter_provinsi_dan_jenis(klien):
    j = klien.get("/api/ringkasan", params={"provinsi": "11", "jenis": B}).json()
    assert j["total_kejadian"] == 9 
    assert [p["jenis_bencana"] for p in j["per_jenis"]] == [B]


def test_detail_wilayah(klien):
    r = klien.get("/api/wilayah/1102", params={"tahun_awal": 2020, "tahun_akhir": 2020})
    j = r.json()
    assert j["nama_kabupaten"] == "KAB BETA" and j["provinsi"] == "ACEH"
    assert len(j["lq"]) == 3
    assert j["agregat_per_tahun"] == [{"tahun": 2020, "semua_jenis": 10}]
    assert {t["jenis_bencana"]: t["jumlah"] for t in j["tren"]} == {B: 1, L: 3, K: 4}


def test_detail_wilayah_tidak_ada(klien):
    r = klien.get("/api/wilayah/9999")
    assert r.status_code == 404 and r.json()["detail"] == "Wilayah tidak ditemukan."


@pytest.mark.parametrize("url", [
    "/api/lq?tahun_awal=2021&tahun_akhir=2020",
    "/api/lq?tahun_awal=1999",
    "/api/lq?tahun_akhir=2099",
    "/api/lq?tahun_awal=abc",
    "/api/lq?jenis=GEMPA",
    "/api/lq?provinsi=1",
    "/api/lq?provinsi=99",
    "/api/lq?ukuran=100000",
    "/api/lq?ukuran=0",
    "/api/lq?halaman=0",
    "/api/lq?urut=password",
    "/api/lq?kategori=RAWAN",
    "/api/lq?cari=" + "a" * 51,
    "/api/wilayah/12",
    "/api/wilayah/abcd",
    "/api/ringkasan?provinsi=ab",
])
def test_masukan_tidak_valid_ditolak(klien, url):
    assert klien.get(url).status_code in (404, 422)
    assert klien.get(url).status_code != 500

def test_cors_hanya_origin_yang_diizinkan(klien):
    ok = klien.get("/api/health", headers={"Origin": "http://localhost:5173"})
    asing = klien.get("/api/health", headers={"Origin": "https://jahat.example"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "access-control-allow-origin" not in asing.headers


def test_metode_selain_get_ditolak(klien):
    assert klien.post("/api/lq").status_code == 405
    assert klien.delete("/api/wilayah/1101").status_code == 405


def test_kesalahan_server_tidak_membocorkan_detail(engine):
    app = create_app(engine)

    @app.get("/api/rusak")
    def rusak():
        raise RuntimeError("rahasia internal D:\\DisasterInsight\\backend")

    r = TestClient(app, raise_server_exceptions=False).get("/api/rusak")
    assert r.status_code == 500
    assert r.json() == {"detail": "Terjadi kesalahan pada server."}
    assert "rahasia" not in r.text
