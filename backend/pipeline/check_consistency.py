import sys
from pathlib import Path

import pandas as pd
from load_aggregate import load_aggregate
from load_events import RAW_DIR, ROOT

CLEAN_CSV = ROOT / "data" / "clean" / "kejadian_2018_2023.csv"
DOCS_DIR = ROOT / "docs"


def cari_file_agregat(argumen: list) -> Path:
    if argumen:
        return Path(argumen[0])
    kandidat = sorted(RAW_DIR.glob("Kejadian_Bencana.*"))
    if len(kandidat) != 1:
        sys.exit(
            "File agregat tidak ditemukan otomatis. "
            "Jalankan dengan nama file: python pipeline/check_consistency.py <path>"
        )
    return kandidat[0]


def uji(kejadian: pd.DataFrame, agregat: pd.DataFrame) -> dict:
    kode_agregat = set(agregat["kode_kabupaten"])

    luar = kejadian[~kejadian["kode_kabupaten"].isin(kode_agregat)]
    luar_ringkas = (
        luar.groupby(["kode_kabupaten", "nama_kabupaten", "provinsi"])
        .size()
        .rename("jumlah_kejadian")
        .reset_index()
        .sort_values("jumlah_kejadian", ascending=False)
    )

    kode_kejadian = set(kejadian["kode_kabupaten"])
    tanpa_kejadian = agregat[~agregat["kode_kabupaten"].isin(kode_kejadian)]
    jumlah_tanpa_kejadian = tanpa_kejadian["kode_kabupaten"].nunique()

    tiga = (
        kejadian.groupby(["kode_kabupaten", "tahun"]).size().rename("tiga_jenis").reset_index()
    )
    gabung = agregat.merge(tiga, on=["kode_kabupaten", "tahun"], how="left")
    gabung["tiga_jenis"] = gabung["tiga_jenis"].fillna(0).astype(int)
    gabung["selisih"] = gabung["jumlah_semua_jenis"] - gabung["tiga_jenis"]
    pelanggaran = gabung[gabung["selisih"] < 0].sort_values("selisih")

    per_tahun = gabung.groupby("tahun").agg(
        agregat=("jumlah_semua_jenis", "sum"), tiga_jenis=("tiga_jenis", "sum")
    )
    per_tahun["porsi_tiga_jenis_%"] = (per_tahun["tiga_jenis"] / per_tahun["agregat"] * 100).round(1)

    return {
        "luar": luar_ringkas,
        "jumlah_kejadian_luar": len(luar),
        "jumlah_tanpa_kejadian": jumlah_tanpa_kejadian,
        "jumlah_sel": len(gabung),
        "pelanggaran": pelanggaran,
        "per_tahun": per_tahun,
    }


def tulis_laporan(h: dict) -> str:
    pel = h["pelanggaran"]
    baris = [
        "# Laporan Uji Konsistensi Data Agregat vs Data Kejadian",
        "",
        "Dibuat otomatis oleh `backend/pipeline/check_consistency.py`.",
        "",
        "## Cakupan kode kabupaten",
        f"- Kode di data kejadian yang tidak ada di file agregat: {len(h['luar'])} kode ({h['jumlah_kejadian_luar']} kejadian)",
        f"- Kode di file agregat tanpa satu pun kejadian banjir/longsor/karhutla: {h['jumlah_tanpa_kejadian']}",
        "",
        "## Pasangan kabupaten-tahun yang melanggar aturan",
        f"- Total pasangan diuji: {h['jumlah_sel']}",
        f"- Pelanggaran (3 jenis > agregat): {len(pel)}",
        "",
        "## Porsi tiga jenis terhadap total semua jenis, per tahun",
        "```",
        h["per_tahun"].to_string(),
        "```",
        "",
    ]
    if len(h["luar"]):
        baris += ["## Kode tidak cocok (20 teratas)", "```", h["luar"].head(20).to_string(index=False), "```", ""]
    if len(pel):
        baris += ["## Pelanggaran terbesar (20 teratas)", "```", pel.head(20).to_string(index=False), "```", ""]
    return "\n".join(baris)


if __name__ == "__main__":
    agregat = load_aggregate(cari_file_agregat(sys.argv[1:]))
    kejadian = pd.read_csv(CLEAN_CSV, dtype={"kode_kabupaten": str})
    laporan = tulis_laporan(uji(kejadian, agregat))
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "laporan_konsistensi_agregat.md").write_text(laporan, encoding="utf-8")
    print(laporan)