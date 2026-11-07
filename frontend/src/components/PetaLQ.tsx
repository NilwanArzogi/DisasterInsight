import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import type { FeatureCollection } from 'geojson'
import 'leaflet/dist/leaflet.css'

type Baris = {
  kode_kabupaten: string
  nama_kabupaten: string
  provinsi: string
  jenis_bencana: string
  e_ik: number
  e_i_semua: number
  lq: number | null
  status: string
  kategori: string
  data_sedikit: boolean
}

const JENIS = ['BANJIR', 'TANAH LONGSOR', 'KEBAKARAN HUTAN DAN LAHAN']
const UKURAN = 50

const KELAS = [
  { min: 0, warna: '#deebf7', label: '< 0,5' },
  { min: 0.5, warna: '#bdd7e7', label: '0,5 – 1' },
  { min: 1, warna: '#6baed6', label: '1 – 2' },
  { min: 2, warna: '#3182bd', label: '2 – 4' },
  { min: 4, warna: '#08519c', label: '≥ 4' },
]
const ABU = '#d4d4d8'
const KOSONG = '#ffffff'

function warna(b?: Baris) {
  if (!b) return ABU
  if (b.kategori === 'tidak ada laporan') return KOSONG
  if (b.lq == null || b.status !== 'ok') return ABU
  let w = KELAS[0].warna
  for (const k of KELAS) if (b.lq >= k.min) w = k.warna
  return w
}

const esc = (s: string) => s.replace(/[&<>"']/g, c => `&#${c.charCodeAt(0)};`)

function popup(nama: string, prov: string, b?: Baris) {
  const kepala = `<b>${esc(nama ?? '')}</b><br/>${esc(prov ?? '')}`
  if (!b) return `${kepala}<br/><i>Tidak ada data LQ untuk wilayah ini.</i>`
  return (
    `${kepala}<br/>${esc(b.jenis_bencana)}` +
    `<br/>LQ: <b>${b.lq == null ? '–' : b.lq.toFixed(3)}</b> (${esc(b.kategori)})` +
    `<br/>Kejadian jenis ini: ${b.e_ik}; seluruh jenis bencana: ${b.e_i_semua}` +
    (b.data_sedikit
      ? '<br/><i>Total kejadian sedikit: LQ mudah berubah drastis, tafsirkan dengan hati-hati.</i>'
      : '')
  )
}

async function ambilSemua(jenis: string): Promise<Baris[]> {
  const hasil: Baris[] = []
  for (let halaman = 1; halaman < 40; halaman++) {
    const q = new URLSearchParams({ jenis, halaman: String(halaman), ukuran: String(UKURAN) })
    const r = await fetch(`/api/lq?${q}`)
    if (!r.ok) throw new Error(`HTTP ${r.status}`)
    const j = await r.json()
    hasil.push(...j.data)
    if (j.data.length < UKURAN || hasil.length >= j.meta.jumlah_total) break
  }
  return hasil
}

export default function PetaLQ() {
  const el = useRef<HTMLDivElement>(null)
  const peta = useRef<L.Map | null>(null)
  const lapis = useRef<L.GeoJSON | null>(null)
  const [geo, setGeo] = useState<FeatureCollection | null>(null)
  const [data, setData] = useState<Map<string, Baris> | null>(null)
  const [jenis, setJenis] = useState(JENIS[0])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!el.current || peta.current) return
    const m = L.map(el.current).setView([-2.5, 118], 5)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 12,
      attribution: '© OpenStreetMap | Batas: BIG (edisi Sep 2023)',
    }).addTo(m)
    peta.current = m
    return () => {
      m.remove()
      peta.current = null
      lapis.current = null
    }
  }, [])

  useEffect(() => {
    fetch('/data/kabkota.geojson')
      .then(r => {
        if (!r.ok) throw new Error(`GeoJSON HTTP ${r.status}`)
        return r.json()
      })
      .then(setGeo)
      .catch(e => setError(e.message))
  }, [])

  useEffect(() => {
    let batal = false
    setData(null)
    setError(null)
    ambilSemua(jenis)
      .then(rows => {
        if (!batal) setData(new Map(rows.map(r => [r.kode_kabupaten, r])))
      })
      .catch(e => {
        if (!batal) setError(e.message)
      })
    return () => {
      batal = true
    }
  }, [jenis])

  useEffect(() => {
    if (!peta.current || !geo || !data) return
    lapis.current?.remove()
    lapis.current = L.geoJSON(geo, {
      style: f => {
        const b = data.get(f?.properties.kode)
        return {
          fillColor: warna(b),
          fillOpacity: 0.9,
          color: b?.data_sedikit ? '#0f172a' : '#64748b',
          weight: b?.data_sedikit ? 1 : 0.4,
          dashArray: b?.data_sedikit ? '2 2' : undefined,
        }
      },
      onEachFeature: (f, layer) => {
        const p = f.properties
        layer.bindPopup(popup(p.nama, p.provinsi, data.get(p.kode)))
      },
    }).addTo(peta.current)
  }, [geo, data])

  return (
    <section className="mt-8 rounded-lg bg-white p-4 shadow">
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <h2 className="text-lg font-semibold text-slate-800">Peta LQ per kabupaten/kota</h2>
        <select
          value={jenis}
          onChange={e => setJenis(e.target.value)}
          className="rounded border border-slate-300 px-2 py-1 text-sm"
        >
          {JENIS.map(j => (
            <option key={j}>{j}</option>
          ))}
        </select>
        {!data && !error && <span className="text-sm text-slate-500">Memuat data...</span>}
      </div>

      {error && <div className="mb-3 rounded bg-red-100 p-2 text-sm text-red-700">Gagal memuat: {error}</div>}

      <div ref={el} className="h-[520px] w-full rounded" />

      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-600">
        <span className="font-medium">LQ (konsentrasi relatif):</span>
        {KELAS.map(k => (
          <span key={k.label} className="flex items-center gap-1">
            <i className="inline-block h-3 w-3 border border-slate-400" style={{ background: k.warna }} />
            {k.label}
          </span>
        ))}
        <span className="flex items-center gap-1">
          <i className="inline-block h-3 w-3 border border-slate-400" style={{ background: KOSONG }} />
          tidak ada laporan
        </span>
        <span className="flex items-center gap-1">
          <i className="inline-block h-3 w-3 border border-slate-400" style={{ background: ABU }} />
          tidak ada data / tidak dapat dihitung
        </span>
        <span>Garis putus-putus: total kejadian sedikit</span>
      </div>
    </section>
  )
}