import pandas as pd
from load_events import ROOT, load_all_events

PERIODE_AWAL = pd.Timestamp("2018-01-01")
PERIODE_AKHIR = pd.Timestamp("2023-12-31")

CLEAN_DIR = ROOT / "data" / "clean"
DOCS_DIR = ROOT / "docs"
CROSSWALK_CSV = ROOT / "backend" / "reference" / "crosswalk_kode.csv"

NORMALISASI_PROVINSI = {
    "DAERAH ISTIMEWA YOGYAKARTA": "DI YOGYAKARTA",
    "P A P U A": "PAPUA",
}

KUNCI_IDENTIK = ["kode_kabupaten", "tanggal", "jenis_bencana", "lokasi", "penyebab"]
KUNCI_KAB_TGL_JENIS = ["kode_kabupaten", "tanggal", "jenis_bencana"]


def terapkan_padanan(df: pd.DataFrame) -> pd.DataFrame:
    padanan = pd.read_csv(CROSSWALK_CSV, dtype=str)
    peta = dict(zip(padanan["kode_lama"], padanan["kode_baru"]))
    df["kode_asal"] = df["kode_kabupaten"]
    df["kode_kabupaten"] = df["kode_kabupaten"].replace(peta)
    return df


def bersihkan(data: pd.DataFrame):
    ringkasan = pd.DataFrame(index=sorted(data["jenis_bencana"].unique()))
    ringkasan["dimuat"] = data.groupby("jenis_bencana").size()

    df = data[data["tanggal"].between(PERIODE_AWAL, PERIODE_AKHIR)].copy()
    ringkasan["dalam_periode"] = df.groupby("jenis_bencana").size()

    df["provinsi"] = df["provinsi"].replace(NORMALISASI_PROVINSI)
    df = terapkan_padanan(df)

    identik = df.duplicated(subset=KUNCI_IDENTIK)
    ringkasan["identik_dihapus"] = df[identik].groupby("jenis_bencana").size()
    df = df[~identik].copy()
    ringkasan["tersisa"] = df.groupby("jenis_bencana").size()

    df["ganda_kab_tgl_jenis"] = df.duplicated(subset=KUNCI_KAB_TGL_JENIS, keep=False)
    ringkasan["ditandai_ganda"] = (
        df[df["ganda_kab_tgl_jenis"]].groupby("jenis_bencana").size()
    )

    df["tahun"] = df["tanggal"].dt.year
    return df, ringkasan.fillna(0).astype(int)


def tulis_laporan(df: pd.DataFrame, ringkasan: pd.DataFrame) -> str:
    per_tahun = pd.crosstab(df["tahun"], df["jenis_bencana"])
    variasi_nama = df.groupby("kode_kabupaten")["nama_kabupaten"].nunique()
    dipadankan = (df["kode_asal"] != df["kode_kabupaten"]).sum()
    baris = [
        "# Laporan Kualitas Data Kejadian (2018-2023)",
        "",
        "Dibuat otomatis oleh `backend/pipeline/clean_events.py`.",
        "",
        "## Ringkasan per jenis bencana",
        "```",
        ringkasan.to_string(),
        "```",
        "",
        "## Jumlah kejadian per tahun (setelah pembersihan)",
        "```",
        per_tahun.to_string(),
        "```",
        "",
        "## Wilayah",
        f"- Kode kabupaten unik: {df['kode_kabupaten'].nunique()}",
        f"- Nilai provinsi unik: {df['provinsi'].nunique()}",
        f"- Kode kabupaten dengan lebih dari satu ejaan nama: {(variasi_nama > 1).sum()}",
        f"- Baris dengan kode lama Papua yang dipadankan ke kode baru: {dipadankan}",
        "",
        "## Aturan yang diterapkan",
        f"- Periode: {PERIODE_AWAL.date()} sampai {PERIODE_AKHIR.date()}",
        "- Kode lama Papua dipadankan ke kode baru (backend/reference/crosswalk_kode.csv)",
        "- Baris identik penuh (kabupaten, tanggal, jenis, lokasi, penyebab) dihapus",
        "- Baris dengan kabupaten, tanggal, dan jenis sama ditandai, tidak dihapus",
        "- Provinsi dinormalisasi: " + ", ".join(
            f"{a} -> {b}" for a, b in NORMALISASI_PROVINSI.items()
        ),
        "",
    ]
    return "\n".join(baris)


if __name__ == "__main__":
    mentah = load_all_events()
    bersih, ringkasan = bersihkan(mentah)

    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    kolom_keluaran = [
        "kode_kabupaten", "kode_asal", "nama_kabupaten", "provinsi",
        "tanggal", "tahun", "jenis_bencana", "ganda_kab_tgl_jenis",
    ]
    bersih[kolom_keluaran].to_csv(CLEAN_DIR / "kejadian_2018_2023.csv", index=False)

    laporan = tulis_laporan(bersih, ringkasan)
    (DOCS_DIR / "laporan_kualitas_data.md").write_text(laporan, encoding="utf-8")
    print(laporan)
