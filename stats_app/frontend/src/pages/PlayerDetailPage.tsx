import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchPlayerDetail, PlayerDetail } from '../api/client'

function formatPlaytime(seconds: number): string {
  if (!seconds) return '—'
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  return `${hours}h ${minutes}m`
}

function levelBadgeColor(level: number): string {
  if (level >= 250) return 'bg-gradient-to-br from-red-500 to-red-700'
  if (level >= 200) return 'bg-gradient-to-br from-orange-500 to-red-600'
  if (level >= 150) return 'bg-gradient-to-br from-yellow-500 to-orange-600'
  if (level >= 100) return 'bg-gradient-to-br from-amber-500 to-yellow-600'
  if (level >= 50)  return 'bg-gradient-to-br from-emerald-500 to-emerald-700'
  return 'bg-gradient-to-br from-zinc-500 to-zinc-700'
}

function StatCard({ label, value, accent }: { label: string; value: string | number; accent?: string }) {
  return (
    <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4">
      <div className="text-xs text-zinc-400 uppercase tracking-wide mb-1">{label}</div>
      <div className={`text-2xl font-bold ${accent ?? 'text-zinc-100'}`}>{value}</div>
    </div>
  )
}

function BarRow({ name, value, max, color }: {
  name: string; value: number; max: number; color: string
}) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="w-44 truncate" title={name}>{name}</span>
      <div className="flex-1 bg-zinc-800 rounded h-5 overflow-hidden relative">
        <div className={`${color} h-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-12 text-right tabular-nums font-medium">{value}</span>
    </div>
  )
}

export default function PlayerDetailPage() {
  const { steamId } = useParams<{ steamId: string }>()
  const [data, setData] = useState<PlayerDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!steamId) return
    setLoading(true)
    setError(null)
    fetchPlayerDetail(steamId)
      .then(setData)
      .catch((err) => setError(err?.response?.data?.detail ?? err.message ?? 'unknown error'))
      .finally(() => setLoading(false))
  }, [steamId])

  if (loading) {
    return <div className="max-w-6xl mx-auto p-6 text-zinc-400">Завантаження…</div>
  }
  if (error || !data) {
    return (
      <div className="max-w-6xl mx-auto p-6">
        <div className="bg-red-900/30 border border-red-700 text-red-200 p-4 rounded mb-4">
          {error ?? 'Гравець не знайдений'}
        </div>
        <Link to="/" className="text-amber-400 hover:underline">← До лідерборду</Link>
      </div>
    )
  }

  const p = data.profile
  const maxKilled = Math.max(1, ...data.most_killed.map((x) => x.kills))
  const maxKillers = Math.max(1, ...data.killed_by.map((x) => x.deaths))
  const maxWeapon = Math.max(1, ...data.top_weapons.map((x) => x.kills))

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="mb-4">
        <Link to="/" className="text-zinc-400 hover:text-amber-400 text-sm">← До лідерборду</Link>
      </div>

      {/* Header */}
      <div className="mb-6 flex items-center gap-4 flex-wrap">
        <span
          className={`inline-flex items-center justify-center min-w-[3rem] px-3 py-2 rounded text-lg font-bold text-white ${levelBadgeColor(
            p.level,
          )}`}
        >
          {p.level}
        </span>
        <h1 className="text-3xl font-bold flex-1 break-all">{p.name}</h1>
        <span className="text-xs text-zinc-500 font-mono">{p.steam_id}</span>
      </div>

      {/* Overview stats */}
      <section className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3 mb-6">
        <StatCard label="Kills"          value={p.kills.toLocaleString('uk-UA')} accent="text-green-400" />
        <StatCard label="Deaths"         value={p.deaths.toLocaleString('uk-UA')} accent="text-red-400" />
        <StatCard label="K/D"            value={p.kd_ratio ?? '—'} accent="text-amber-400" />
        <StatCard label="KPM"            value={p.kpm ?? '—'} />
        <StatCard label="Час гри"        value={formatPlaytime(p.total_seconds)} />
        <StatCard label="Матчів"         value={p.matches_played} />
        <StatCard label="Team Kills"     value={p.teamkills} accent="text-amber-500" />
        <StatCard label="Combat"         value={p.combat?.toLocaleString('uk-UA') ?? '—'} />
        <StatCard label="Offense"        value={p.offense?.toLocaleString('uk-UA') ?? '—'} />
        <StatCard label="Defense"        value={p.defense?.toLocaleString('uk-UA') ?? '—'} />
        <StatCard label="Support"        value={p.support?.toLocaleString('uk-UA') ?? '—'} />
        <StatCard label="Best kill streak" value={p.best_kills_streak ?? '—'} accent="text-emerald-400" />
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* PVP: most killed */}
        <section>
          <h2 className="text-amber-400 uppercase text-xs tracking-widest mb-3">
            🎯 Найчастіші жертви
          </h2>
          <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4 space-y-2">
            {data.most_killed.length === 0 && <div className="text-zinc-600 text-sm">немає даних</div>}
            {data.most_killed.map((v) => (
              <BarRow key={v.victim} name={v.victim} value={v.kills} max={maxKilled}
                color="bg-gradient-to-r from-green-700 to-green-500" />
            ))}
          </div>
        </section>

        {/* PVP: killers */}
        <section>
          <h2 className="text-red-400 uppercase text-xs tracking-widest mb-3">
            💀 Найзлісніші вбивці
          </h2>
          <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4 space-y-2">
            {data.killed_by.length === 0 && <div className="text-zinc-600 text-sm">немає даних</div>}
            {data.killed_by.map((k) => (
              <BarRow key={k.killer} name={k.killer} value={k.deaths} max={maxKillers}
                color="bg-gradient-to-r from-red-700 to-red-500" />
            ))}
          </div>
        </section>

        {/* Weapons */}
        <section>
          <h2 className="text-blue-400 uppercase text-xs tracking-widest mb-3">
            🔫 Улюблена зброя
          </h2>
          <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4 space-y-2">
            {data.top_weapons.length === 0 && <div className="text-zinc-600 text-sm">немає даних</div>}
            {data.top_weapons.map((w) => (
              <BarRow key={w.weapon} name={w.weapon} value={w.kills} max={maxWeapon}
                color="bg-gradient-to-r from-blue-700 to-blue-500" />
            ))}
          </div>
        </section>
      </div>

      {/* Recent matches */}
      <section className="mt-6">
        <h2 className="text-zinc-300 uppercase text-xs tracking-widest mb-3">
          Останні матчі
        </h2>
        <div className="overflow-x-auto bg-zinc-900/40 border border-zinc-800 rounded-lg">
          <table className="w-full text-sm">
            <thead className="bg-zinc-800 text-zinc-300 text-xs uppercase">
              <tr>
                <th className="p-3 text-left">Дата</th>
                <th className="p-3 text-left">Карта</th>
                <th className="p-3 text-right">K</th>
                <th className="p-3 text-right">D</th>
                <th className="p-3 text-right">K/D</th>
                <th className="p-3 text-right">Combat</th>
                <th className="p-3 text-right">Support</th>
              </tr>
            </thead>
            <tbody>
              {data.recent_matches.map((m, i) => (
                <tr key={i} className="border-t border-zinc-800">
                  <td className="p-3 text-zinc-400 text-xs whitespace-nowrap">
                    {m.match_date ? new Date(m.match_date).toLocaleDateString('uk-UA') : '—'}
                  </td>
                  <td className="p-3">{m.map_name}</td>
                  <td className="p-3 text-right text-green-400">{m.kills}</td>
                  <td className="p-3 text-right text-red-400">{m.deaths}</td>
                  <td className="p-3 text-right">{m.kd?.toFixed?.(2) ?? '—'}</td>
                  <td className="p-3 text-right">{m.combat}</td>
                  <td className="p-3 text-right">{m.support}</td>
                </tr>
              ))}
              {data.recent_matches.length === 0 && (
                <tr><td colSpan={7} className="p-6 text-center text-zinc-500">немає матчів</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
