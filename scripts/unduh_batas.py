"""Unduh batas kabupaten/kota resmi BIG -> frontend/public/data/kabkota.geojson
Hanya memakai pustaka standar Python."""
import csv, json, re, sys, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]          
LQ_CSV = ROOT / "data" / "output" / "lq_2018_2023.csv"
CROSSWALK = ROOT / "backend" / "reference" / "crosswalk_kode.csv"
OUT = ROOT / "frontend" / "public" / "data" / "kabkota.geojson"
URL = ("https://geoservices.big.go.id/rbi/rest/services/Hosted/"
       "Wilayah_Administrasi_Kabupaten__Kota/FeatureServer/0/query")
UKURAN = 100


def ambil(offset):
    p = {
        "where": "1=1", "outFields": "kdpkab,wadmkk,wadmpr,namobj",
        "returnGeometry": "true", "outSR": "4326", "f": "json",
        "orderByFields": "objectid", "resultOffset": offset,
        "resultRecordCount": UKURAN,
        "geometryPrecision": "4", "maxAllowableOffset": "0.005",
    }
    req = urllib.request.Request(URL + "?" + urllib.parse.urlencode(p),
                                 headers={"User-Agent": "DisasterInsight/1.0"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.load(r)


def luas(r): 
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(r, r[1:] + r[:1])) / 2


def ke_poligon(rings):
    """Esri: ring luar searah jarum jam, lubang berlawanan."""
    polys = []
    for r in rings:
        r = [p[:2] for p in r]
        if luas(r) < 0:
            polys.append([r])
        elif polys:
            polys[-1].append(r)
    return polys


with open(LQ_CSV, encoding="utf-8-sig") as f:
    rd = csv.DictReader(f)
    if "kode_kabupaten" not in rd.fieldnames:
        sys.exit(f"Kolom kode_kabupaten tidak ada. Kolom: {rd.fieldnames}")
    nama_api = {}
    for r in rd:
        nama_api[str(r["kode_kabupaten"]).strip()] = (
            f'{r.get("nama_kabupaten", "")} ({r.get("provinsi", "")})')
kode_api = set(nama_api)

with open(CROSSWALK, encoding="utf-8-sig") as f:
    cw = {r["kode_lama"].strip(): r["kode_baru"].strip() for r in csv.DictReader(f)}

semua, offset = [], 0
while True:
    d = ambil(offset)
    if "error" in d:
        sys.exit(f"Error dari server BIG: {d['error']}")
    batch = d.get("features", [])
    semua += batch
    print(f"  diunduh {len(semua)} fitur")
    if len(batch) < UKURAN:
        break
    offset += len(batch)

gab, dikonversi, dilewati = {}, [], 0
for ft in semua:
    a, g = ft["attributes"], ft.get("geometry")
    kode = re.sub(r"\D", "", str(a.get("kdpkab") or ""))
    if not g or len(kode) != 4:
        dilewati += 1
        continue
    if kode not in kode_api and kode in cw:
        dikonversi.append((kode, cw[kode]))
        kode = cw[kode]
    e = gab.setdefault(kode, {"nama": a.get("wadmkk") or a.get("namobj"),
                              "prov": a.get("wadmpr"), "polys": []})
    e["polys"] += ke_poligon(g["rings"])

fitur = [{
    "type": "Feature",
    "properties": {"kode": k, "nama": e["nama"], "provinsi": e["prov"]},
    "geometry": {"type": "MultiPolygon", "coordinates": e["polys"]},
} for k, e in sorted(gab.items()) if e["polys"]]

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"type": "FeatureCollection", "features": fitur},
                          ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

kode_geo = set(gab)
print(f"\nDisimpan: {OUT}  ({OUT.stat().st_size / 1e6:.2f} MB)")
print(f"Fitur BIG: {len(semua)} | dilewati (tanpa kode/geometri): {dilewati}")
print(f"Wilayah di peta: {len(kode_geo)} | kode di data LQ: {len(kode_api)}")
print(f"Kode dikonversi lewat crosswalk: {len(dikonversi)}")

print("\nKode LQ tanpa poligon:")
for k in sorted(kode_api - kode_geo):
    print("  ", k, nama_api[k])

print("\nPoligon tanpa data LQ:")
for k in sorted(kode_geo - kode_api):
    print("  ", k, gab[k]["nama"], f'({gab[k]["prov"]})')