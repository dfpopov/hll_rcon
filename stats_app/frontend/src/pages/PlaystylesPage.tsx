/**
 * Server-wide list of playstyle archetypes. Each card shows the description,
 * player count, and top-5 sample players (by kills). Whole card is a link
 * to /playstyles/{id} for the full paginated list.
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchPlaystyles, PlaystyleStat } from '../api/client'
import Avatar from '../components/Avatar'

export default function PlaystylesPage() {
  const [data, setData] = useState<PlaystyleStat[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    fetchPlaystyles().then(setData).finally(() => setLoading(false))
  }, [])

  const total = data.reduce((s, p) => s + p.player_count, 0)
  const sorted = [...data].sort((a, b) => b.player_count - a.player_count)

  return (
    <div className="max-w-6xl mx-auto p-6">
      <header className="mb-6">
        <h1 className="text-3xl font-bold mb-1">🎭 Стилі гри</h1>
        <p className="text-zinc-400 text-sm">
          {data.length} архетипів • {total.toLocaleString('uk-UA')} класифікованих гравців
        </p>
      </header>

      {loading && <div className="text-zinc-400 py-8 text-center">Завантаження…</div>}

      {!loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {sorted.map((ps) => {
            const pct = total > 0 ? (ps.player_count / total * 100) : 0
            return (
              <Link key={ps.id} to={`/playstyles/${ps.id}`}
                className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4
                           hover:border-amber-700/40 hover:bg-zinc-900 transition-all block">
                <div className="flex items-baseline gap-2 mb-1">
                  <span className="text-3xl">{ps.emoji}</span>
                  <h3 className={`font-semibold text-lg flex-1 ${ps.color}`}>{ps.title}</h3>
                  <span className="text-sm font-bold tabular-nums text-zinc-200">{ps.player_count}</span>
                </div>
                <p className="text-xs text-zinc-500 mb-3 italic">{ps.description}</p>
                <div className="h-1.5 bg-zinc-800 rounded overflow-hidden mb-2">
                  <div className={`h-full ${ps.color.replace('text-', 'bg-')}`} style={{ width: `${pct}%` }} />
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-zinc-500">{pct.toFixed(1)}% усіх</span>
                </div>
                {ps.sample_players.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-zinc-800">
                    <div className="text-[10px] uppercase text-zinc-600 tracking-widest mb-1">Топ гравці</div>
                    <div className="flex flex-wrap gap-1.5">
                      {ps.sample_players.map((s) => (
                        <span key={s.steam_id}
                          className="inline-flex items-center gap-1 text-xs bg-zinc-800/60 rounded px-1.5 py-0.5"
                          title={`${s.kills} kills, ${s.matches_played} матчів`}>
                          <Avatar url={s.avatar_url} name={s.name} size={16} />
                          <span className="truncate max-w-[120px]">{s.name}</span>
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </Link>
            )
          })}
        </div>
      )}
    </div>
  )
}
