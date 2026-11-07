import { useEffect, useState } from 'react'
import PetaLQ from './components/PetaLQ'
import TabelLQ from './components/TabelLQ'

type Ringkasan = Record<string, unknown>

const label = (k: string) => k.replace(/_/g, ' ').replace(/^\w/, c => c.toUpperCase())
const fmt = (v: unknown) => (typeof v === 'number' ? v.toLocaleString('id-ID') : String(v))

export default function App() {
  const [data, setData] = useState<Ringkasan | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/ringkasan')
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then(setData)
      .catch(e => setError(e.message))
  }, [])

  const kpis = data
    ? Object.entries(data).filter(
        ([k, v]) => k !== 'catatan_metode' && (typeof v === 'number' || typeof v === 'string'),
      )
    : []

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <h1 className="text-2xl font-bold text-slate-800">DisasterInsight Indonesia</h1>
      <p className="mb-6 text-sm text-slate-500">
        Analisis Location Quotient kejadian bencana, 2018–2023
      </p>

      {error && (
        <div className="rounded bg-red-100 p-3 text-red-700">
          Gagal memuat API: {error}. Pastikan uvicorn masih berjalan.
        </div>
      )}
      {!data && !error && <p className="text-slate-500">Memuat...</p>}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {kpis.map(([k, v]) => (
          <div key={k} className="rounded-lg bg-white p-4 shadow">
            <div className="text-sm text-slate-500">{label(k)}</div>
            <div className="text-2xl font-semibold text-slate-800">{fmt(v)}</div>
          </div>
        ))}
      </div>

      <PetaLQ />
      <TabelLQ />

      {typeof data?.catatan_metode === 'string' && (
        <p className="mt-6 rounded bg-amber-50 p-3 text-xs text-slate-600">
          <b>Catatan metode.</b> {data.catatan_metode}
        </p>
      )}
    </div>
  )
}