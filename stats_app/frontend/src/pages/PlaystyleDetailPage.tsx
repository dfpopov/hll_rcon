/**
 * Paginated list of all players matching one playstyle archetype.
 */
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchPlaystylePlayers, PlaystylePlayersResponse } from '../api/client'
import Avatar from '../components/Avatar'
import LevelBadge from '../components/LevelBadge'
import CountryFlag from '../components/CountryFlag'
import MiniCompareButton from '../components/MiniCompareButton'

const PAGE_SIZE = 50

export default function PlaystyleDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [data, setData] = useState<PlaystylePlayersResponse | null>(null)
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    setLoading(true)
    fetchPlaystylePlayers(id, PAGE_SIZE, page * PAGE_SIZE)
      .then(setData)
      .finally(() => setLoading(false))
  }, [id, page])

  if (!id) return null

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0

  return (
    <div className="max-w-5xl mx-auto p-6">
      <Link to="/playstyles" className="text-zinc-400 hover:text-amber-400 text-sm">← Усі стилі</Link>

      <header className="mt-3 mb-6">
        {data?.playstyle && (
          <>
            <div className="flex items-baseline gap-3 mb-2">
              <span className="text-4xl">{data.playstyle.emoji}</span>
              <h1 className={`text-3xl font-bold ${data.playstyle.color}`}>{data.playstyle.title}</h1>
            </div>
            <p className="text-zinc-200 text-base italic mb-2">📜 {data.playstyle.description}</p>
            <p className="text-zinc-400 text-sm">
              {data.total.toLocaleString('uk-UA')} гравців з цим стилем
              {data.primary_count !== data.total && (
                <> · з них {data.primary_count.toLocaleString('uk-UA')} як основний, {(data.total - data.primary_count).toLocaleString('uk-UA')} як вторинний</>
              )}
            </p>
          </>
        )}
      </header>

      {loading && <div className="text-zinc-400 py-8 text-center">Завантаження…</div>}

      {!loading && data && (
        <>
          <div className="overflow-x-auto bg-zinc-900/40 border border-zinc-800 rounded-lg">
            <table className="w-full text-sm">
              <thead className="bg-zinc-800 text-zinc-300 text-xs uppercase">
                <tr>
                  <th className="p-3 text-left w-12">#</th>
                  <th className="p-3 text-left">Гравець</th>
                  <th className="p-3 text-right">Kills</th>
                  <th className="p-3 text-right">K/D</th>
                  <th className="p-3 text-right">Матчів</th>
                  <th className="p-3 text-right">Год</th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((r, i) => (
                  <tr key={r.steam_id} className="border-t border-zinc-800 hover:bg-zinc-700/20">
                    <td className="p-3 text-zinc-500">{page * PAGE_SIZE + i + 1}</td>
                    <td className="p-3">
                      <div className="flex items-center gap-2">
                        <Avatar url={r.avatar_url ?? null} name={r.name} size={28} />
                        <LevelBadge level={r.level} />
                        <CountryFlag iso={r.country ?? null} />
                        <Link to={`/player/${r.steam_id}`}
                          className="font-medium hover:text-amber-400 transition-colors">
                          {r.name}
                        </Link>
                        {r.is_primary === false && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-500 border border-zinc-700"
                            title="Для цього гравця стиль — другорядний">також</span>
                        )}
                        <MiniCompareButton steam_id={r.steam_id} name={r.name} />
                      </div>
                    </td>
                    <td className="p-3 text-right text-green-400">{r.kills}</td>
                    <td className="p-3 text-right">{r.kd_ratio ?? '—'}</td>
                    <td className="p-3 text-right text-zinc-400">{r.matches_played}</td>
                    <td className="p-3 text-right text-zinc-400">{Math.floor(r.total_seconds / 3600)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between mt-4 text-sm flex-wrap gap-3">
            <div className="text-zinc-400">
              {data.total > 0
                ? `${page * PAGE_SIZE + 1}–${page * PAGE_SIZE + data.count} з ${data.total.toLocaleString('uk-UA')}`
                : 'Немає гравців'}
            </div>
            <div className="flex items-center gap-2">
              <button onClick={() => setPage(0)} disabled={page === 0}
                className="px-3 py-1 rounded bg-zinc-800 hover:bg-zinc-700 disabled:opacity-30">« Перша</button>
              <button onClick={() => setPage(Math.max(0, page - 1))} disabled={page === 0}
                className="px-3 py-1 rounded bg-zinc-800 hover:bg-zinc-700 disabled:opacity-30">‹</button>
              <span className="text-zinc-300 px-2">{page + 1} з {totalPages || 1}</span>
              <button onClick={() => setPage(Math.min(totalPages - 1, page + 1))} disabled={page >= totalPages - 1}
                className="px-3 py-1 rounded bg-zinc-800 hover:bg-zinc-700 disabled:opacity-30">›</button>
              <button onClick={() => setPage(totalPages - 1)} disabled={page >= totalPages - 1}
                className="px-3 py-1 rounded bg-zinc-800 hover:bg-zinc-700 disabled:opacity-30">Остан. »</button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
