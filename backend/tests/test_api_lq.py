import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture(scope="module")
def client():
    with TestClient(create_app()) as c:
        yield c


def ambil_lq(client, kode, jenis):
    r = client.get(f"/api/wilayah/{kode}")
    assert r.status_code == 200
    for baris in r.json()["lq"]:
        if baris["jenis_bencana"] == jenis:
            return baris
    raise AssertionError(f"{jenis} tidak ada untuk {kode}")


def test_ringkasan_total_kejadian(client):
    r = client.get("/api/ringkasan")
    assert r.status_code == 200
    assert r.json()["total_kejadian"] == 18337


def test_bogor_longsor(client):
    b = ambil_lq(client, "3201", "TANAH LONGSOR")
    assert b["e_ik"] == 723
    assert b["e_i_semua"] == 1349
    assert b["e_nasional_semua"] == 26671
    assert b["lq"] == pytest.approx(2.631, abs=0.001)


def test_mahakam_ulu_longsor_data_sedikit(client):
    b = ambil_lq(client, "6411", "TANAH LONGSOR")
    assert (b["e_ik"], b["e_i_semua"], b["e_nasional_k"]) == (2, 2, 5433)
    assert b["lq"] == pytest.approx(4.909, abs=0.001)
    assert b["data_sedikit"] is True


def test_mahakam_ulu_banjir_tidak_ada_laporan(client):
    b = ambil_lq(client, "6411", "BANJIR")
    assert b["e_ik"] == 0
    assert b["lq"] == 0.0
    assert b["status"] == "tidak_ada_laporan"


@pytest.mark.parametrize("kode", ["3201", "6411", "1101"])
def test_rumus_lq_konsisten_dengan_komponen(client, kode):
    """LQ = (e_ik / e_i_semua) / (e_nasional_k / e_nasional_semua)"""
    for b in client.get(f"/api/wilayah/{kode}").json()["lq"]:
        if b["e_i_semua"] == 0:
            continue
        harapan = (b["e_ik"] / b["e_i_semua"]) / (b["e_nasional_k"] / b["e_nasional_semua"])
        assert b["lq"] == pytest.approx(harapan, rel=1e-6)