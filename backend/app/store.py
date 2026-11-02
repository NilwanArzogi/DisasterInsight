import pandas as pd

from pipeline.lq import AMBANG_MINIMUM, JENIS_FOKUS, hitung_lq


class DataStore:
    def __init__(self, data: dict):
        self.wilayah = data["wilayah"]
        self.kejadian = data["kejadian"]
        self.sumber = data["sumber"]

        nama = self.wilayah.rename(columns={"kode": "kode_kabupaten", "nama": "nama_kabupaten"})
        self.agregat = data["agregat"].merge(
            nama[["kode_kabupaten", "nama_kabupaten"]], on="kode_kabupaten", how="left"
        )
        self.agregat["nama_kabupaten"] = self.agregat["nama_kabupaten"].fillna("")

        self.tahun_min = int(self.agregat["tahun"].min())
        self.tahun_max = int(self.agregat["tahun"].max())
        self.jenis = list(JENIS_FOKUS)
        self.ambang_minimum = AMBANG_MINIMUM
        self.provinsi = (
            self.wilayah[["kode_provinsi", "provinsi"]]
            .drop_duplicates()
            .sort_values("kode_provinsi")
            .reset_index(drop=True)
        )
        self.nama_wilayah = self.wilayah.set_index("kode")["nama"].to_dict()
        self.nama_provinsi = self.wilayah.set_index("kode")["provinsi"].to_dict()
        self._cache = {}

    def lq(self, tahun_awal: int, tahun_akhir: int) -> pd.DataFrame:
        kunci = (tahun_awal, tahun_akhir)
        if kunci not in self._cache:
            hasil = hitung_lq(self.kejadian, self.agregat, tahun_awal, tahun_akhir)
            hasil = hasil.merge(
                self.wilayah.rename(columns={"kode": "kode_kabupaten"})[["kode_kabupaten", "kode_provinsi", "provinsi"]],
                on="kode_kabupaten", how="left",
            )
            self._cache[kunci] = hasil
        return self._cache[kunci]
