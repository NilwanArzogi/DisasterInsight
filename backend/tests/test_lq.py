"""Uji perhitungan LQ. Dataset kecil di bawah ini dapat dihitung dengan tangan.

Skenario (tahun 2020), E = jumlah kejadian:
              banjir  longsor  karhutla | semua jenis (agregat)
  kabupaten A    6       2        0     |   10
  kabupaten B    1       3        4     |   10
  kabupaten C    3       0        0     |    5
  nasional      10       5        4     |   25

Contoh hitungan tangan:
  LQ(A,banjir)   = (6/10) / (10/25) = 0.6 / 0.4  = 1.5
  LQ(B,karhutla) = (4/10) / (4/25)  = 0.4 / 0.16 = 2.5
  LQ(B,banjir)   = (1/10) / (10/25) = 0.1 / 0.4  = 0.25
  LQ(A,longsor)  = (2/10) / (5/25)  = 0.2 / 0.2  = 1.0
"""
import math

import pandas as pd
import pytest
from lq import hitung_lq, kategori_lq, lq_satu

B, L, K = "BANJIR", "TANAH LONGSOR", "KEBAKARAN HUTAN DAN LAHAN"


def buat_kejadian(spesifikasi, tahun=2020):
    """spesifikasi: {(kode, jenis): jumlah}. Tiap baris diberi tanggal berbeda."""
    baris = []
    for (kode, jenis), jumlah in spesifikasi.items():
        for n in range(jumlah):
            tanggal = pd.Timestamp(f"{tahun}-01-01") + pd.Timedelta(days=n)
            baris.append(
                {"kode_kabupaten": kode, "tanggal": tanggal, "tahun": tahun, "jenis_bencana": jenis}
            )
    return pd.DataFrame(baris, columns=["kode_kabupaten", "tanggal", "tahun", "jenis_bencana"])


def buat_agregat(total, tahun=2020):
    return pd.DataFrame(
        [
            {"kode_kabupaten": k, "nama_kabupaten": f"KAB {k}", "tahun": tahun, "jumlah_semua_jenis": v}
            for k, v in total.items()
        ],
        columns=["kode_kabupaten", "nama_kabupaten", "tahun", "jumlah_semua_jenis"],
    )


@pytest.fixture
def data_kecil():
    kejadian = buat_kejadian(
        {("A", B): 6, ("A", L): 2, ("B", B): 1, ("B", L): 3, ("B", K): 4, ("C", B): 3}
    )
    agregat = buat_agregat({"A": 10, "B": 10, "C": 5})
    return kejadian, agregat


def ambil(hasil, kode, jenis):
    return hasil[(hasil["kode_kabupaten"] == kode) & (hasil["jenis_bencana"] == jenis)].iloc[0]


# ---------- kasus normal (hitungan tangan) ----------
def test_lq_normal_sesuai_hitungan_tangan(data_kecil):
    hasil = hitung_lq(*data_kecil, tahun_awal=2020, tahun_akhir=2020)
    assert ambil(hasil, "A", B)["lq"] == pytest.approx(1.5)
    assert ambil(hasil, "B", K)["lq"] == pytest.approx(2.5)
    assert ambil(hasil, "B", B)["lq"] == pytest.approx(0.25)
    assert ambil(hasil, "B", L)["lq"] == pytest.approx(1.5)
    assert ambil(hasil, "C", B)["lq"] == pytest.approx(1.5)


def test_komponen_dan_jumlah_baris(data_kecil):
    hasil = hitung_lq(*data_kecil, tahun_awal=2020, tahun_akhir=2020)
    assert len(hasil) == 3 * 3  # 3 kabupaten x 3 jenis
    baris = ambil(hasil, "A", B)
    assert (baris["e_ik"], baris["e_i_semua"], baris["e_nasional_k"], baris["e_nasional_semua"]) == (6, 10, 10, 25)


def test_rata_rata_tertimbang_lq_sama_dengan_satu(data_kecil):
    """Sifat LQ: rata-rata LQ yang diberi bobot E(i,semua) selalu sama dengan 1."""
    hasil = hitung_lq(*data_kecil, tahun_awal=2020, tahun_akhir=2020)
    for jenis in (B, L, K):
        sub = hasil[hasil["jenis_bencana"] == jenis]
        rata = (sub["lq"] * sub["e_i_semua"]).sum() / sub["e_i_semua"].sum()
        assert rata == pytest.approx(1.0)


# ---------- nilai nol ----------
def test_tidak_ada_laporan_jenis_ini_bernilai_nol(data_kecil):
    hasil = hitung_lq(*data_kecil, tahun_awal=2020, tahun_akhir=2020)
    baris = ambil(hasil, "A", K)
    assert baris["lq"] == 0.0
    assert baris["status"] == "tidak_ada_laporan"
    assert baris["kategori"] == "tidak ada laporan"


def test_penyebut_wilayah_nol_tidak_dapat_dihitung():
    lq, status = lq_satu(0, 0, 10, 25)
    assert math.isnan(lq) and status == "tidak_dapat_dihitung"


def test_penyebut_nasional_nol_tidak_dapat_dihitung():
    assert lq_satu(0, 5, 0, 25)[1] == "tidak_dapat_dihitung"  # jenis ini nol di seluruh Indonesia
    assert lq_satu(0, 5, 3, 0)[1] == "tidak_dapat_dihitung"


def test_kabupaten_tanpa_kejadian_jenis_fokus_tetap_dihitung():
    kejadian = buat_kejadian({("A", B): 2})
    agregat = buat_agregat({"A": 4, "Z": 6})  # Z hanya punya jenis bencana lain
    hasil = hitung_lq(kejadian, agregat, tahun_awal=2020, tahun_akhir=2020)
    baris = ambil(hasil, "Z", B)
    assert baris["e_ik"] == 0 and baris["status"] == "tidak_ada_laporan"


# ---------- data kosong ----------
def test_data_kejadian_kosong_tidak_error():
    kejadian = buat_kejadian({})
    agregat = buat_agregat({"A": 5})
    hasil = hitung_lq(kejadian, agregat, tahun_awal=2020, tahun_akhir=2020)
    assert (hasil["status"] == "tidak_dapat_dihitung").all()


def test_semua_kosong_menghasilkan_tabel_kosong():
    hasil = hitung_lq(buat_kejadian({}), buat_agregat({}), tahun_awal=2020, tahun_akhir=2020)
    assert len(hasil) == 0
    assert "lq" in hasil.columns


# ---------- batas interpretasi ----------
def test_kategori_tepat_satu(data_kecil):
    hasil = hitung_lq(*data_kecil, tahun_awal=2020, tahun_akhir=2020)
    assert ambil(hasil, "A", L)["lq"] == pytest.approx(1.0)
    assert ambil(hasil, "A", L)["kategori"] == "LQ = 1"


def test_kategori_batas():
    assert kategori_lq(1.0, "ok") == "LQ = 1"
    assert kategori_lq(1.0 + 1e-12, "ok") == "LQ = 1"  # selisih kesalahan pembulatan
    assert kategori_lq(1.000001, "ok") == "LQ > 1"
    assert kategori_lq(0.999999, "ok") == "LQ < 1"
    assert kategori_lq(math.nan, "tidak_dapat_dihitung") == "tidak dapat dihitung"


# ---------- aturan penyebut dan satuan ----------
def test_penyebut_memakai_maksimum_agregat_dan_jenis_fokus():
    kejadian = buat_kejadian({("A", B): 8})
    agregat = buat_agregat({"A": 5})  # lebih kecil dari 8 -> penyebut dikoreksi jadi 8
    hasil = hitung_lq(kejadian, agregat, tahun_awal=2020, tahun_akhir=2020)
    assert ambil(hasil, "A", B)["e_i_semua"] == 8


def test_filter_periode_tahun():
    k = pd.concat([buat_kejadian({("A", B): 4}, tahun=2019), buat_kejadian({("A", B): 2}, tahun=2020)])
    a = pd.concat([buat_agregat({"A": 4}, tahun=2019), buat_agregat({"A": 3}, tahun=2020)])
    hasil = hitung_lq(k, a, tahun_awal=2020, tahun_akhir=2020)
    baris = ambil(hasil, "A", B)
    assert (baris["e_ik"], baris["e_i_semua"]) == (2, 3)


def test_satuan_kab_hari_jenis_membuang_baris_ganda():
    kejadian = buat_kejadian({("A", B): 3})
    kejadian = pd.concat([kejadian, kejadian.iloc[[0]]])  # satu baris ganda di kabupaten, tanggal, jenis sama
    agregat = buat_agregat({"A": 10})
    baris = ambil(hitung_lq(kejadian, agregat, tahun_awal=2020, tahun_akhir=2020), "A", B)
    unik = ambil(hitung_lq(kejadian, agregat, tahun_awal=2020, tahun_akhir=2020, satuan="kab_hari_jenis"), "A", B)
    assert baris["e_ik"] == 4 and unik["e_ik"] == 3


def test_peringatan_data_sedikit(data_kecil):
    hasil = hitung_lq(*data_kecil, tahun_awal=2020, tahun_akhir=2020, ambang_minimum=10)
    assert not ambil(hasil, "A", B)["data_sedikit"]  # penyebut 10
    assert ambil(hasil, "C", B)["data_sedikit"]  # penyebut 5


# ---------- masukan tidak valid ----------
def test_jumlah_negatif_ditolak():
    with pytest.raises(ValueError):
        lq_satu(-1, 5, 3, 10)


def test_pembilang_melebihi_penyebut_ditolak():
    with pytest.raises(ValueError):
        lq_satu(6, 5, 3, 10)


def test_satuan_tidak_dikenal_ditolak(data_kecil):
    with pytest.raises(ValueError):
        hitung_lq(*data_kecil, satuan="minggu")