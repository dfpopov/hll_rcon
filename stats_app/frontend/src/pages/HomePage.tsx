import { useEffect, useState } from 'react'
import { fetchTopKills, TopKillsRow } from '../api/client'

export default function HomePage() {
  const [rows, setRows] = useState<TopKillsRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchTopKills(50)
      .then((data) => setRows(data.results))
      .catch((err) => setError(err.message ?? 'unknown error'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="max-w-6xl mx-auto p-6">
      <header className="mb-6">
        <h1 className="text-3xl font-bold mb-2">HLL Stats — All time</h1>
        <p className="text-zinc-400">Топ гравці за всю історію матчів</p>
      </header>

      {loading && <div className="text-zinc-400">Завантаження…</div>}
      {error && (
        <div className="bg-red-900/30 border border-red-700 text-red-200 p-4 rounded">
          Помилка: {error}
        </div>
      )}
      {!loading && !error && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-zinc-800 text-zinc-300 uppercase text-xs">
              <tr>
                <th className="p-3 text-left">#</th>
                <th className="p-3 text-left">Гравець</th>
                <th className="p-3 text-right">Рівень</th>
                <th className="p-3 text-right">Kills</th>
                <th className="p-3 text-right">Deaths</th>
                <th className="p-3 text-right">TK</th>
                <th className="p-3 text-right">K/D</th>
                <th className="p-3 text-right">KPM</th>
                <th className="p-3 text-right">Матчів</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={r.steam_id} className="odd:bg-zinc-900 even:bg-zinc-800/40 hover:bg-zinc-700/30">
                  <td className="p-3 text-zinc-500">{i + 1}</td>
                  <td className="p-3 font-medium">{r.name}</td>
                  <td className="p-3 text-right text-zinc-400">{r.level}</td>
                  <td className="p-3 text-right text-green-400">{r.kills}</td>
                  <td className="p-3 text-right text-red-400">{r.deaths}</td>
                  <td className="p-3 text-right text-amber-400">{r.teamkills}</td>
                  <td className="p-3 text-right">{r.kd_ratio ?? '—'}</td>
                  <td className="p-3 text-right">{r.kpm ?? '—'}</td>
                  <td className="p-3 text-right text-zinc-400">{r.matches_played}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
