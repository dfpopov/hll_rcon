import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { fetchAchievementPlayers, fetchAchievementStats, AchievementHoldersResponse, AchievementStat } from '../api/client'
import { useMetaLabel } from '../i18n/metaLabel'
import LevelBadge from '../components/LevelBadge'
import Avatar from '../components/Avatar'
import CountryFlag from '../components/CountryFlag'
import MiniCompareButton from '../components/MiniCompareButton'

const PAGE_SIZE = 50

export default function AchievementDetailPage() {
  const { t, i18n } = useTranslation()
  const meta = useMetaLabel()
  const nf = new Intl.NumberFormat(i18n.resolvedLanguage || i18n.language || 'en')
  const { id } = useParams<{ id: string }>()
  const [holders, setHolders] = useState<AchievementHoldersResponse | null>(null)
  const [stat, setStat] = useState<AchievementStat | null>(null)
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    fetchAchievementStats()
      .then((all) => setStat(all.find((a) => a.id === id) ?? null))
      .catch(() => {})
  }, [id])

  useEffect(() => {
    if (!id) return
    setLoading(true)
    fetchAchievementPlayers(id, PAGE_SIZE, page * PAGE_SIZE)
      .then(setHolders)
      .finally(() => setLoading(false))
  }, [id, page])

  if (!id) return null

  const totalPages = holders ? Math.ceil(holders.total / PAGE_SIZE) : 0

  return (
    <div className="max-w-5xl mx-auto p-6">
      <Link to="/achievements" className="text-zinc-400 hover:text-amber-400 text-sm">{t('achievementDetail.backToAll')}</Link>

      <header className="mt-3 mb-6">
        <div className="flex items-baseline gap-3 mb-2">
          {stat && <span className="text-4xl">{stat.icon}</span>}
          {/* Title + description resolve via meta.achievements.<id> with the
              Ukrainian backend string as fallback. */}
          <h1 className="text-3xl font-bold">{stat ? meta.title('achievements', stat.id, stat.title) : id}</h1>
          {stat && <span className="text-xs uppercase text-zinc-500 tracking-widest">{stat.tier}</span>}
        </div>
        {stat?.description && (
          <p className="text-zinc-200 text-base mb-2 italic">📜 {meta.description('achievements', stat.id, stat.description)}</p>
        )}
        {stat && (
          <p className="text-zinc-400 text-sm">
            {t('achievementDetail.summary', {
              earned: nf.format(stat.earned_count),
              total: nf.format(stat.total_players),
              pct: stat.percentage,
            })}
          </p>
        )}
      </header>

      {loading && <div className="text-zinc-400 py-8 text-center">{t('common.loading')}</div>}

      {!loading && holders && (
        <>
          <div className="overflow-x-auto bg-zinc-900/40 border border-zinc-800 rounded-lg">
            <table className="w-full text-sm">
              <thead className="bg-zinc-800 text-zinc-300 text-xs uppercase">
                <tr>
                  <th className="p-3 text-left w-12">{t('table.rank')}</th>
                  <th className="p-3 text-left">{t('table.player')}</th>
                  <th className="p-3 text-right">{t('table.kills')}</th>
                  <th className="p-3 text-right">{t('table.kd')}</th>
                  <th className="p-3 text-right">{t('table.matches')}</th>
                  <th className="p-3 text-right">{t('table.hoursShort')}</th>
                </tr>
              </thead>
              <tbody>
                {holders.results.map((r, i) => (
                  <tr key={r.steam_id} className="border-t border-zinc-800 hover:bg-zinc-700/20">
                    <td className="p-3 text-zinc-500">{page * PAGE_SIZE + i + 1}</td>
                    <td className="p-3">
                      <div className="flex items-center gap-2">
                        <Avatar url={r.avatar_url} name={r.name} size={28} />
                        <LevelBadge level={r.level} />
                        <CountryFlag iso={r.country} />
                        <Link to={`/player/${r.steam_id}`}
                          className="font-medium hover:text-amber-400 transition-colors">
                          {r.name}
                        </Link>
                        <MiniCompareButton steam_id={r.steam_id} name={r.name} />
                      </div>
                    </td>
                    <td className="p-3 text-right text-green-400">{r.kills}</td>
                    <td className="p-3 text-right">{r.kd_ratio ?? '—'}</td>
                    <td className="p-3 text-right text-zinc-400">{r.matches_played}</td>
                    <td className="p-3 text-right text-zinc-400">
                      {Math.floor(r.total_seconds / 3600)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between mt-4 text-sm flex-wrap gap-3">
            <div className="text-zinc-400">
              {holders.total > 0
                ? t('pagination.rangeOf', { start: page * PAGE_SIZE + 1, end: page * PAGE_SIZE + holders.count, total: nf.format(holders.total) })
                : t('playstyles.detail.noPlayers')}
            </div>
            <div className="flex items-center gap-2">
              <button onClick={() => setPage(0)} disabled={page === 0}
                className="px-3 py-1 rounded bg-zinc-800 hover:bg-zinc-700 disabled:opacity-30">{t('pagination.first')}</button>
              <button onClick={() => setPage(Math.max(0, page - 1))} disabled={page === 0}
                className="px-3 py-1 rounded bg-zinc-800 hover:bg-zinc-700 disabled:opacity-30">‹</button>
              <span className="text-zinc-300 px-2">{t('pagination.pageOf', { current: page + 1, total: totalPages || 1 })}</span>
              <button onClick={() => setPage(Math.min(totalPages - 1, page + 1))} disabled={page >= totalPages - 1}
                className="px-3 py-1 rounded bg-zinc-800 hover:bg-zinc-700 disabled:opacity-30">›</button>
              <button onClick={() => setPage(totalPages - 1)} disabled={page >= totalPages - 1}
                className="px-3 py-1 rounded bg-zinc-800 hover:bg-zinc-700 disabled:opacity-30">{t('pagination.last')}</button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
