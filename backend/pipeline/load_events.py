from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"

EVENT_FILES = {
    "BANJIR": "Banjir.xlsx",
    "TANAH LONGSOR": "Tanah_Longsor.xlsx",
    "KEBAKARAN HUTAN DAN LAHAN": "Kebakaran_Hutan_dan_Lahan.xlsx",
}

COLUMN_MAP = {
    "ID Kabupaten": "kode_kabupaten",
    "Tanggal Kejadian": "tanggal",
    "Kejadian": "jenis_bencana",
    "Kabupaten": "nama_kabupaten",
    "Provinsi": "provinsi",
    "Lokasi": "lokasi",    
    "Penyebab": "penyebab",  
}


def load_event_file(path: Path) -> pd.DataFrame:
    """Baca satu file kejadian. Baris 1 berisi judul, header ada di baris 2."""
    df = pd.read_excel(
        path,
        header=1,
        usecols=list(COLUMN_MAP),
        dtype={"ID Kabupaten": str},
    )
    df = df.rename(columns=COLUMN_MAP)
    df["tanggal"] = pd.to_datetime(df["tanggal"], errors="coerce")
    df["kode_kabupaten"] = df["kode_kabupaten"].str.strip().str.zfill(4)
    for kolom in ["jenis_bencana", "nama_kabupaten", "provinsi"]:
        df[kolom] = df[kolom].str.strip().str.upper()
    df["sumber_file"] = path.name
    return df


def load_all_events() -> pd.DataFrame:
    frames = []
    for jenis, nama_file in EVENT_FILES.items():
        df = load_event_file(RAW_DIR / nama_file)
        salah = df["jenis_bencana"] != jenis
        if salah.any():
            raise ValueError(
                f"{nama_file}: {salah.sum()} baris tidak berjenis {jenis}"
            )
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


if __name__ == "__main__":
    data = load_all_events()
    ringkasan = data.groupby("jenis_bencana").agg(
        baris=("tanggal", "size"),
        tanggal_awal=("tanggal", "min"),
        tanggal_akhir=("tanggal", "max"),
    )
    print(ringkasan)
    print("Total baris:", len(data))
    print("Tanggal kosong:", data["tanggal"].isna().sum())
    print(
        "Kode kabupaten bukan 4 digit:",
        (~data["kode_kabupaten"].str.fullmatch(r"\d{4}")).sum(),
    )