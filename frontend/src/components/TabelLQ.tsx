import { useEffect, useState } from 'react'

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
type Opsi = {
  jenis_bencana: string[]
  provinsi: { kode: string; nama: string }[]
  kategori: string[]
}
type Filter = { jenis: string; provinsi: string; cari: string; kategori: string }

const UKURAN = 50
const PROV_PAKAI: 'nama' | 'kode' = 'nama'

function buatQuery(f: Filter, halaman: number) {
  const q = new URLSearchParams({ halaman: String(halaman), ukuran: String(UKURAN) })
  if (f.jenis) q.set('jenis', f.jenis)
  if (f.provinsi) q.set('provinsi', f.provinsi)
  if (f.cari) q.set('cari', f.cari)
  if (f.kategori) q.set('kategori', f.kategori)
  return q
}

const csvSel = (v: unknown) => {
  const s = v == null ? '' : String(v)
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}

export default function TabelLQ() {
  const [opsi, setOpsi] = useState<Opsi | null>(null)
  const [filter, setFilter] = useState<Filter>({ jenis: '', provinsi: '', cari: '', kategori: '' })
  const [cariInput, setCariInput] = useState('')
  const [halaman, setHalaman] = useState(1)
  const [rows, setRows] = useState<Baris[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [mengekspor, setMengekspor] = useState(false)

  useEffect(() => {
    fetch('/api/opsi').then(r => r.json()).then(setOpsi).catch(e => setError(e.message))
  }, [])

  useEffect(() => {
    const t = setTimeout(() => {
      setFilter(f => (f.cari === cariInput ? f : { ...f, cari: cariInput }))
      setHalaman(1)
    }, 400)
    return () => clearTimeout(t)
  }, [cariInput])

  useEffect(() => {
    let batal = false
    setLoading(true)
    setError(null)
    fetch(`/api/lq?${buatQuery(filter, halaman)}`)
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then(j => {
        if (batal) return
        setRows(j.data)
        setTotal(j.meta.jumlah_total)
      })
      .catch(e => !batal && setError(e.message))
      .finally(() => !batal && setLoading(false))
    return () => {
      batal = true
    }
  }, [filter, halaman])

  const ubah = (k: keyof Filter, v: string) => {
    setFilter(f => ({ ...f, [k]: v }))
    setHalaman(1)
  }

  const jumlahHalaman = Math.max(1, Math.ceil(total / UKURAN))

  async function ekspor() {
    setMengekspor(true)
    setError(null)
    try {
      const semua: Baris[] = []
      for (let h = 1; h <= 100; h++) {
        const r = await fetch(`/api/lq?${buatQuery(filter, h)}`)
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        const j = await r.json()
        semua.push(...j.data)
        if (j.data.length < UKURAN || semua.length >= j.meta.jumlah_total) break
      }
      const kolom: (keyof Baris)[] = [
        'kode_kabupaten', 'nama_kabupaten', 'provinsi', 'jenis_bencana',
        'e_ik', 'e_i_semua', 'lq', 'status', 'kategori', 'data_sedikit',
      ]
      const csv = [kolom.join(','), ...semua.map(r => kolom.map(k => csvSel(r[k])).join(','))].join('\r\n')
      const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' })
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = 'lq_disasterinsight.csv'
      a.click()
      URL.revokeObjectURL(a.href)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Gagal mengekspor')
    } finally {
      setMengekspor(false)
    }
  }

  const sel = 'rounded border border-slate-300 px-2 py-1 text-sm'

  return (
    <section className="mt-8 rounded-lg bg-white p-4 shadow">
      <h2 className="mb-3 text-lg font-semibold text-slate-800">Tabel LQ</h2>

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <select className={sel} value={filter.jenis} onChange={e => ubah('jenis', e.target.value)}>
          <option value="">Semua jenis bencana</option>
          {opsi?.jenis_bencana.map(j => <option key={j}>{j}</option>)}
        </select>
        <select className={sel} value={filter.provinsi} onChange={e => ubah('provinsi', e.target.value)}>
          <option value="">Semua provinsi</option>
          {opsi?.provinsi.map(p => (
            <option key={p.kode} value={p[PROV_PAKAI]}>{p.nama}</option>
          ))}
        </select>
        <select className={sel} value={filter.kategori} onChange={e => ubah('kategori', e.target.value)}>
          <option value="">Semua kategori</option>
          {opsi?.kategori.map(k => <option key={k}>{k}</option>)}
        </select>
        <input
          className={sel}
          placeholder="Cari kabupaten/kota..."
          value={cariInput}
          onChange={e => setCariInput(e.target.value)}
        />
        <button
          onClick={ekspor}
          disabled={mengekspor || total === 0}
          className="ml-auto rounded bg-slate-800 px-3 py-1 text-sm text-white disabled:opacity-50"
        >
          {mengekspor ? 'Mengekspor...' : `Ekspor CSV (${total.toLocaleString('id-ID')} baris)`}
        </button>
      </div>

      {error && <div className="mb-3 rounded bg-red-100 p-2 text-sm text-red-700">Gagal memuat: {error}</div>}

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="border-b text-slate-500">
            <tr>
              <th className="py-2 pr-3">Kabupaten/Kota</th>
              <th className="pr-3">Provinsi</th>
              <th className="pr-3">Jenis</th>
              <th className="pr-3 text-right">Kejadian jenis ini</th>
              <th className="pr-3 text-right">Seluruh kejadian</th>
              <th className="pr-3 text-right">LQ</th>
              <th>Kategori</th>
            </tr>
          </thead>
          <tbody className={loading ? 'opacity-50' : ''}>
            {rows.map(r => (
              <tr key={`${r.kode_kabupaten}-${r.jenis_bencana}`} className="border-b last:border-0">
                <td className="py-1.5 pr-3">
                  {r.nama_kabupaten}
                  {r.data_sedikit && (
                    <span className="ml-1 text-xs text-amber-600" title="Total kejadian sedikit: LQ mudah berubah drastis">
                      ⚠
                    </span>
                  )}
                </td>
                <td className="pr-3">{r.provinsi}</td>
                <td className="pr-3">{r.jenis_bencana}</td>
                <td className="pr-3 text-right">{r.e_ik.toLocaleString('id-ID')}</td>
                <td className="pr-3 text-right">{r.e_i_semua.toLocaleString('id-ID')}</td>
                <td className="pr-3 text-right font-medium">{r.lq == null ? '–' : r.lq.toFixed(3)}</td>
                <td>{r.kategori}</td>
              </tr>
            ))}
            {!loading && rows.length === 0 && (
              <tr><td colSpan={7} className="py-4 text-center text-slate-500">Tidak ada data untuk filter ini.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="mt-3 flex items-center gap-3 text-sm">
        <button className={sel} disabled={halaman <= 1} onClick={() => setHalaman(h => h - 1)}>← Sebelumnya</button>
        <span>Halaman {halaman} dari {jumlahHalaman}</span>
        <button className={sel} disabled={halaman >= jumlahHalaman} onClick={() => setHalaman(h => h + 1)}>Berikutnya →</button>
      </div>
    </section>
  )
}