from typing import Dict, List, Optional

from pydantic import BaseModel

CATATAN_METODE = (
    "LQ adalah ukuran konsentrasi relatif jumlah kejadian yang dilaporkan, dibandingkan dengan "
    "seluruh Indonesia. LQ bukan probabilitas, bukan prediksi, dan bukan peta rawan bencana resmi BNPB. "
    "LQ tidak mempertimbangkan jumlah penduduk, luas wilayah, paparan, kerentanan, maupun kapasitas penanggulangan."
)


class Periode(BaseModel):
    awal: int
    akhir: int


class Sumber(BaseModel):
    nama: str
    url: str
    keterangan: str
    diimpor_pada: str


class ProvinsiOpsi(BaseModel):
    kode: str
    nama: str


class ResponOpsi(BaseModel):
    tahun_min: int
    tahun_max: int
    jenis_bencana: List[str]
    provinsi: List[ProvinsiOpsi]
    kategori: List[str]
    ambang_data_sedikit: int
    sumber: List[Sumber]
    catatan_metode: str


class BarisLQ(BaseModel):
    kode_kabupaten: str
    nama_kabupaten: str
    provinsi: str
    jenis_bencana: str
    e_ik: int
    e_i_semua: int
    e_nasional_k: int
    e_nasional_semua: int
    lq: Optional[float]
    status: str
    kategori: str
    data_sedikit: bool


class MetaLQ(BaseModel):
    periode: Periode
    jumlah_total: int
    halaman: int
    ukuran: int
    ambang_data_sedikit: int
    catatan_metode: str


class ResponLQ(BaseModel):
    meta: MetaLQ
    data: List[BarisLQ]


class JumlahJenis(BaseModel):
    jenis_bencana: str
    jumlah: int


class WilayahTertinggi(BaseModel):
    kode_kabupaten: str
    nama_kabupaten: str
    provinsi: str
    jumlah: int


class TitikTren(BaseModel):
    tahun: int
    jenis_bencana: str
    jumlah: int


class RingkasanKategori(BaseModel):
    jenis_bencana: str
    kategori: Dict[str, int]


class ResponRingkasan(BaseModel):
    periode: Periode
    total_kejadian: int
    per_jenis: List[JumlahJenis]
    wilayah_tertinggi: List[WilayahTertinggi]
    tren: List[TitikTren]
    ringkasan_lq: List[RingkasanKategori]
    catatan_metode: str


class AgregatTahun(BaseModel):
    tahun: int
    semua_jenis: int


class ResponWilayah(BaseModel):
    kode_kabupaten: str
    nama_kabupaten: str
    provinsi: str
    periode: Periode
    lq: List[BarisLQ]
    tren: List[TitikTren]
    agregat_per_tahun: List[AgregatTahun]
    sumber: List[Sumber]
    catatan_metode: str
