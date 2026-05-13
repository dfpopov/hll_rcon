import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { fetchPlayerDetail, findPlayerByName, PlayerDetail } from '../api/client'
import { useCompareList } from '../hooks/useCompareList'
import LevelBadge from '../components/LevelBadge'
import Avatar from '../components/Avatar'
import AchievementBadge from '../components/AchievementBadge'
import CountryFlag from '../components/CountryFlag'
import PlayerRadar from '../components/PlayerRadar'
import ProgressionSparkline from '../components/ProgressionSparkline'
import MiniCompareButton from '../components/MiniCompareButton'
import { formatMapName } from '../components/mapNames'
import { NemesisStamp, LovedHatedMap, PlaystyleCard, matchTitle } from '../components/PlayerMemes'
import TimeOfDayHeatmap from '../components/TimeOfDayHeatmap'

// CRCON public stats site URL — match details available on port 7010
const CRCON_PUBLIC_BASE = 'http://95.111.230.75:7010'

// Weapon class display order + colour (matches weapon_classes.py).
const CLASS_DISPLAY: { name: string; color: string }[] = [
  { name: 'Rifle',           color: 'bg-green-600' },
  { name: 'Submachine Gun',  color: 'bg-emerald-600' },
  { name: 'Machine Gun',     color: 'bg-teal-600' },
  { name: 'Sniper Rifle',    color: 'bg-sky-600' },
  { name: 'Pistol',          color: 'bg-cyan-600' },
  { name: 'Anti-Tank',       color: 'bg-orange-600' },
  { name: 'Tank Gun',        color: 'bg-amber-600' },
  { name: 'Artillery',       color: 'bg-yellow-600' },
  { name: 'Explosive',       color: 'bg-red-600' },
  { name: 'Mine',            color: 'bg-rose-600' },
  { name: 'Flame',           color: 'bg-fuchsia-600' },
  { name: 'Melee',           color: 'bg-violet-600' },
  { name: 'Vehicle Run-over',color: 'bg-pink-600' },
  { name: 'Other',           color: 'bg-zinc-600' },
]

function ClassBreakdownBar({ counts, title }: { counts: Record<string, number>; title: string }) {
  const total = Object.values(counts).reduce((a, b) => a + b, 0)
  if (total === 0) return null
  return (
    <div>
      <div className="text-xs text-zinc-500 uppercase tracking-widest mb-2">{title}</div>
      <div className="flex h-3 rounded overflow-hidden bg-zinc-800">
        {CLASS_DISPLAY.map((c) => {
          const n = counts[c.name] ?? 0
          if (n === 0) return null
          const pct = (n / total) * 100
          return (
            <div key={c.name} className={c.color} style={{ width: `${pct}%` }}
              title={`${c.name}: ${n.toLocaleString('uk-UA')} (${pct.toFixed(1)}%)`} />
          )
        })}
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-1 mt-2 text-xs">
        {CLASS_DISPLAY.map((c) => {
          const n = counts[c.name] ?? 0
          if (n === 0) return null
          const pct = (n / total) * 100
          return (
            <span key={c.name} className="flex items-center gap-1">
              <span className={`inline-block w-2 h-2 rounded-sm ${c.color}`} />
              <span className="text-zinc-300">{c.name}</span>
              <span className="text-zinc-500 tabular-nums">{n.toLocaleString('uk-UA')} ({pct.toFixed(1)}%)</span>
            </span>
          )
        })}
      </div>
    </div>
  )
}

/** Visual divider between thematic blocks on the player profile. */
function SectionDivider({ label }: { label: string }) {
  return (
    <div className="mt-10 mb-4 flex items-center gap-3">
      <h2 className="text-zinc-500 uppercase text-xs tracking-widest whitespace-nowrap">{label}</h2>
      <div className="flex-1 h-px bg-zinc-800" />
    </div>
  )
}


function AddToCompareButton({ steam_id, name }: { steam_id: string; name: string }) {
  const { t } = useTranslation()
  const { has, add, remove, list, max } = useCompareList()
  const inList = has(steam_id)
  const full = !inList && list.length >= max

  const onClick = () => {
    if (inList) {
      remove(steam_id)
    } else {
      const result = add({ steam_id, name })
      if (result === 'full') alert(t('player.compareFull', { max }))
    }
  }

  const label = inList
    ? t('player.inCompareList')
    : full
      ? t('player.listFull', { max })
      : t('player.addToCompare')
  const cls = inList
    ? 'bg-amber-700/40 text-amber-200 border-amber-600/50'
    : full
      ? 'bg-zinc-800 text-zinc-500 border-transparent cursor-not-allowed'
      : 'bg-zinc-800 hover:bg-zinc-700 text-amber-400 hover:text-amber-300 border-transparent'

  return (
    <button onClick={onClick} disabled={full}
      className={`text-xs px-3 py-1 rounded border ${cls}`}
      title={inList ? t('player.removeFromList') : full ? t('player.removeOneFirst') : t('player.addToCompare')}>
      {label}
    </button>
  )
}

function formatPlaytime(seconds: number): string {
  if (!seconds) return '—'
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  return `${hours}h ${minutes}m`
}

function StatCard({ label, value, accent }: { label: string; value: string | number; accent?: string }) {
  return (
    <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4">
      <div className="text-xs text-zinc-400 uppercase tracking-wide mb-1">{label}</div>
      <div className={`text-2xl font-bold ${accent ?? 'text-zinc-100'}`}>{value}</div>
    </div>
  )
}

/**
 * Compact sub-line under a PVP BarRow showing the weapon breakdown for that
 * specific victim / killer. Renders nothing when there are no logged events.
 * Resolves the question "with what weapon did I kill PlayerX in our 5
 * encounters?" — see queries.py:pvp_weapon_breakdown.
 *
 * The "logged" caveat matters: counts here can be ≤ the bar's total because
 * matches without log coverage don't appear in log_lines. We don't surface
 * this caveat per-row to keep the UI quiet — a one-time legend would be
 * better long-term.
 */
function WeaponSubline({ weapons, accent }: { weapons: { weapon: string; count: number }[]; accent: 'green' | 'red' }) {
  if (!weapons.length) return null
  // Show top 4 inline; collapse the rest into a "+N more" pill.
  const shown = weapons.slice(0, 4)
  const rest = weapons.length - shown.length
  const chipCls = accent === 'green'
    ? 'text-green-300/80 border-green-900/50 bg-green-950/30'
    : 'text-red-300/80 border-red-900/50 bg-red-950/30'
  return (
    <div className="flex flex-wrap gap-1 mt-1 ml-44 pl-2 text-xs text-zinc-500">
      {shown.map((w) => (
        <span key={w.weapon}
          className={`inline-flex items-baseline gap-1 px-1.5 py-0.5 rounded border ${chipCls}`}
          title={w.weapon}>
          <span className="truncate max-w-[120px]">{w.weapon}</span>
          <span className="font-medium tabular-nums">×{w.count}</span>
        </span>
      ))}
      {rest > 0 && (
        <span className="text-zinc-600 italic px-1.5 py-0.5">+{rest}</span>
      )}
    </div>
  )
}

function BarRow({ name, value, max, color, onClick }: {
  name: string; value: number; max: number; color: string; onClick?: () => void
}) {
  const { t } = useTranslation()
  const pct = max > 0 ? Math.round((value / max) * 100) : 0
  return (
    <div className="flex items-center gap-2 text-sm">
      <span
        className={`w-44 truncate ${onClick ? 'cursor-pointer hover:text-amber-400 transition-colors' : ''}`}
        title={onClick ? t('player.clickForProfile', { name }) : name}
        onClick={onClick}
      >
        {name}
      </span>
      <div className="flex-1 bg-zinc-800 rounded h-5 overflow-hidden relative">
        <div className={`${color} h-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-12 text-right tabular-nums font-medium">{value}</span>
    </div>
  )
}

export default function PlayerDetailPage() {
  const { t, i18n } = useTranslation()
  const lang = i18n.resolvedLanguage || i18n.language || 'en'
  const nf = new Intl.NumberFormat(lang)
  const { steamId } = useParams<{ steamId: string }>()
  const navigate = useNavigate()
  const [data, setData] = useState<PlayerDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [recentFilter, setRecentFilter] = useState<'all' | 'titled'>('all')

  useEffect(() => {
    if (!steamId) return
    setLoading(true)
    setError(null)
    fetchPlayerDetail(steamId)
      .then(setData)
      .catch((err) => setError(err?.response?.data?.detail ?? err.message ?? 'unknown error'))
      .finally(() => setLoading(false))
  }, [steamId])

  const handlePvpClick = async (name: string) => {
    const sid = await findPlayerByName(name)
    if (sid) {
      navigate(`/player/${encodeURIComponent(sid)}`)
    } else {
      // Show subtle feedback that this name doesn't have a profile
      // (could be opponent from another server, ghost record etc.)
      console.warn('PVP player not found in DB:', name)
    }
  }

  if (loading) {
    return <div className="max-w-6xl mx-auto p-6 text-zinc-400">{t('common.loading')}</div>
  }
  if (error || !data) {
    return (
      <div className="max-w-6xl mx-auto p-6">
        <div className="bg-red-900/30 border border-red-700 text-red-200 p-4 rounded mb-4">
          {error ?? t('player.notFound')}
        </div>
        <Link to="/" className="text-amber-400 hover:underline">{t('player.backToLeaderboard')}</Link>
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
        <Link to="/" className="text-zinc-400 hover:text-amber-400 text-sm">{t('player.backToLeaderboard')}</Link>
      </div>

      {/* Header */}
      <div className="mb-4 flex items-center gap-4 flex-wrap">
        <Avatar url={p.avatar_url} name={p.name} size={80} />
        <LevelBadge level={p.level} size="md" />
        <div className="flex-1 min-w-0">
          <h1 className="text-3xl font-bold break-all">{p.name}</h1>
          {(p.country || p.persona_name) && (
            <div className="text-zinc-400 text-sm mt-1 flex items-center gap-3 flex-wrap">
              {p.country && <CountryFlag iso={p.country} showCode />}
              {p.persona_name && p.persona_name !== p.name && (
                <span className="text-zinc-500">Steam: {p.persona_name}</span>
              )}
            </div>
          )}
          {data.alt_names && data.alt_names.filter((n) => n !== p.name).length > 0 && (
            <div className="text-zinc-500 text-xs mt-2 flex items-center gap-1.5 flex-wrap">
              <span className="uppercase tracking-widest text-zinc-600">Aka:</span>
              {data.alt_names.filter((n) => n !== p.name).slice(0, 8).map((n) => (
                <span key={n} className="px-1.5 py-0.5 rounded bg-zinc-800/60 border border-zinc-800">{n}</span>
              ))}
            </div>
          )}
        </div>
        {p.profile_url && (
          <a href={p.profile_url} target="_blank" rel="noopener noreferrer"
             className="text-xs text-zinc-100 hover:text-white px-3 py-1.5 rounded bg-[#1b2838] hover:bg-[#2a475e] inline-flex items-center gap-1.5 border border-[#2a475e]"
             title={t('player.openSteam')}>
            <svg width="14" height="14" viewBox="0 0 32 32" fill="currentColor" aria-hidden="true">
              <path d="M16 0C7.523 0 .58 6.55.022 14.876l8.605 3.559a4.4 4.4 0 0 1 2.481-.766c.082 0 .164.002.245.006l3.831-5.547v-.077c0-3.34 2.722-6.058 6.058-6.058a6.07 6.07 0 0 1 6.063 6.063 6.07 6.07 0 0 1-6.063 6.058h-.14l-5.464 3.901a4.43 4.43 0 0 1-2.643 4.045 4.43 4.43 0 0 1-5.93-2.265L3.91 21.31C5.755 27.494 10.367 32 16 32c8.836 0 16-7.164 16-16S24.836 0 16 0zm-5.96 24.297l-1.98-.818a3.34 3.34 0 0 0 1.748 1.795 3.34 3.34 0 0 0 4.486-1.683 3.34 3.34 0 0 0 .013-2.55 3.34 3.34 0 0 0-1.74-1.804 3.36 3.36 0 0 0-2.523-.062l2.045.85a2.45 2.45 0 0 1 1.319 3.207 2.45 2.45 0 0 1-3.21 1.319zM25.4 12.05a4.04 4.04 0 0 0-4.038-4.038 4.04 4.04 0 0 0-4.041 4.038 4.04 4.04 0 0 0 4.041 4.041 4.04 4.04 0 0 0 4.038-4.041zm-7.066-.005a3.04 3.04 0 0 1 3.034-3.029 3.04 3.04 0 0 1 3.029 3.029c0 1.67-1.36 3.034-3.029 3.034a3.04 3.04 0 0 1-3.034-3.034z"/>
            </svg>
            Steam
          </a>
        )}
        <AddToCompareButton steam_id={p.steam_id} name={p.name} />
      </div>

      {/* Achievements row */}
      {data.achievements && data.achievements.length > 0 && (
        <section className="mb-6">
          <h2 className="text-zinc-300 uppercase text-xs tracking-widest mb-2">
            {t('nav.achievements')} ({data.achievements.length})
          </h2>
          <div className="flex flex-wrap gap-2">
            {data.achievements.map((a) => (
              <AchievementBadge key={a.id} a={a} />
            ))}
          </div>
        </section>
      )}

      {/* Achievement progress — closest-to-earning badges */}
      {data.achievement_progress && data.achievement_progress.length > 0 && (
        <section className="mb-6">
          <h2 className="text-zinc-300 uppercase text-xs tracking-widest mb-2">
            📈 {t('player.upcomingAchievements')}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-2">
            {data.achievement_progress.map((p) => {
              // Format current/threshold according to the metric scale.
              const fmt = (v: number) => {
                if (p.threshold >= 100000) return nf.format(Math.round(v))
                if (p.threshold >= 3600 && p.id !== 'survivor') {
                  // total_seconds → hours, localized suffix
                  return t('records.allTime.hours', { h: Math.floor(v / 3600) })
                }
                // Ratio thresholds (kd_ratio = 2.0, 3.0) — show 2 decimals
                // so "1.85 / 2.00" is honest instead of being rounded to 2/2.
                if (p.threshold < 10) return v.toFixed(2)
                if (p.threshold % 1 !== 0) return v.toFixed(2)
                return String(Math.round(v))
              }
              return (
                <Link
                  key={p.id}
                  to={`/achievements/${p.id}`}
                  className="bg-zinc-900/60 border border-zinc-800 rounded p-3 hover:border-amber-700/50 hover:bg-zinc-900 transition-colors block"
                  title={t('player.clickToSeeOwners')}
                >
                  <div className="flex items-baseline gap-2 mb-1">
                    <span className="text-xl leading-none">{p.icon}</span>
                    <span className="font-medium text-sm truncate flex-1" title={p.description}>{p.title}</span>
                  </div>
                  <div className="text-xs text-zinc-500 mb-2 truncate" title={p.description}>{p.description}</div>
                  <div className="h-2 bg-zinc-800 rounded overflow-hidden mb-1">
                    <div className="bg-amber-500 h-full" style={{ width: `${p.pct}%` }} />
                  </div>
                  <div className="text-xs text-zinc-400 flex items-baseline justify-between tabular-nums">
                    <span>{fmt(p.current)} / {fmt(p.threshold)}</span>
                    <span className="text-amber-400 font-medium">{p.pct}%</span>
                  </div>
                </Link>
              )
            })}
          </div>
        </section>
      )}

      {/* Playstyle classifier — personality tag derived from score distribution */}
      <PlaystyleCard playstyle={data.playstyle} also={data.playstyle_also} />

      <SectionDivider label={`📊 ${t('player.numbers')}`} />

      {/* Overview stats */}
      <section className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3 mb-6">
        <StatCard label={t('table.kills')}      value={nf.format(p.kills)} accent="text-green-400" />
        <StatCard label={t('table.deaths')}     value={nf.format(p.deaths)} accent="text-red-400" />
        <StatCard label={t('table.kd')}         value={p.kd_ratio ?? '—'} accent="text-amber-400" />
        <StatCard label={t('table.kpm')}        value={p.kpm ?? '—'} />
        <StatCard label={t('table.playtime')}   value={formatPlaytime(p.total_seconds)} />
        <StatCard label={t('table.matches')}    value={p.matches_played} />
        <StatCard label={t('compare.stats.teamkills')} value={p.teamkills} accent="text-amber-500" />
        <StatCard label={t('compare.stats.combat')}    value={p.combat != null ? nf.format(p.combat) : '—'} />
        <StatCard label={t('compare.stats.offense')}   value={p.offense != null ? nf.format(p.offense) : '—'} />
        <StatCard label={t('compare.stats.defense')}   value={p.defense != null ? nf.format(p.defense) : '—'} />
        <StatCard label={t('compare.stats.support')}   value={p.support != null ? nf.format(p.support) : '—'} />
        <StatCard label={t('compare.stats.bestStreak')} value={p.best_kills_streak ?? '—'} accent="text-emerald-400" />
      </section>

      {/* Profile overview: first seen, 100+ kill matches, faction & mode preference */}
      <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        <div className="bg-zinc-900/60 border border-zinc-800 rounded p-3">
          <div className="text-xs text-zinc-500 uppercase tracking-widest">{t('player.firstMatch')}</div>
          <div className="text-base font-medium mt-1">
            {data.overview.first_seen
              ? new Date(data.overview.first_seen).toLocaleDateString(lang, { year: 'numeric', month: 'short', day: 'numeric' })
              : '—'}
          </div>
          <div className="text-xs text-zinc-500 mt-1">{t('player.matchesTotal', { n: data.overview.total_matches })}</div>
        </div>

        <div className="bg-zinc-900/60 border border-zinc-800 rounded p-3">
          <div className="text-xs text-zinc-500 uppercase tracking-widest">{t('player.kill100Matches')}</div>
          <div className="text-2xl font-bold mt-1 tabular-nums text-emerald-400">{data.overview.matches_100plus}</div>
          <div className="text-xs text-zinc-500 mt-1">
            {data.overview.total_matches > 0
              ? t('player.pctOfAllGames', { pct: (data.overview.matches_100plus / data.overview.total_matches * 100).toFixed(2) })
              : '—'}
          </div>
        </div>

        {/* Game mode preference */}
        <div className="bg-zinc-900/60 border border-zinc-800 rounded p-3">
          <div className="text-xs text-zinc-500 uppercase tracking-widest mb-2">{t('player.modes')}</div>
          {(() => {
            const m = data.overview.mode_counts
            const total = m.warfare + m.offensive + m.skirmish
            if (total === 0) return <div className="text-zinc-600 text-sm">{t('records.noData')}</div>
            const seg = (n: number, color: string, label: string) => {
              const pct = n / total * 100
              if (pct < 0.5) return null
              return (
                <div key={label} className="flex items-center gap-2 text-xs">
                  <div className={`h-1.5 ${color} rounded`} style={{ width: `${pct}%` }} />
                  <span className="text-zinc-400 tabular-nums">{label} {pct.toFixed(0)}%</span>
                </div>
              )
            }
            return (
              <div className="space-y-1.5">
                {seg(m.warfare,   'bg-sky-500',    '⚔️ Warfare')}
                {seg(m.offensive, 'bg-orange-500', '🗡 Offensive')}
                {seg(m.skirmish,  'bg-emerald-500','🎯 Skirmish')}
              </div>
            )
          })()}
        </div>

        {/* Faction preference */}
        <div className="bg-zinc-900/60 border border-zinc-800 rounded p-3">
          <div className="text-xs text-zinc-500 uppercase tracking-widest mb-2">
            {t('player.side')} <span className="text-zinc-600 normal-case">{t('player.fromLogs')}</span>
          </div>
          {data.faction_pref.total_known === 0 ? (
            <div className="text-zinc-600 text-sm">{t('player.noLogCoverage')}</div>
          ) : (
            <>
              <div className="flex h-3 rounded overflow-hidden bg-zinc-800">
                <div className="bg-blue-500" style={{ width: `${data.faction_pref.allies_pct}%` }} title={`Allies: ${data.faction_pref.allies}`} />
                <div className="bg-red-500" style={{ width: `${data.faction_pref.axis_pct}%` }} title={`Axis: ${data.faction_pref.axis}`} />
              </div>
              <div className="flex justify-between text-xs mt-2">
                <span className="text-blue-400">🟦 Allies {data.faction_pref.allies_pct}%</span>
                <span className="text-red-400">🟥 Axis {data.faction_pref.axis_pct}%</span>
              </div>
              <div className="text-xs text-zinc-500 mt-1">{t('player.fromKnownMatches', { n: data.faction_pref.total_known })}</div>
            </>
          )}
        </div>
      </section>

      <SectionDivider label={`🎯 ${t('player.howPlays')}`} />

      {/* Win rate — overall + per side */}
      {data.win_rate && data.win_rate.total > 0 && (
        <section className="mb-6 bg-zinc-900/60 border border-zinc-800 rounded-lg p-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
            <div className="text-center">
              <div className="text-xs text-zinc-500 uppercase tracking-widest mb-1">{t('player.winRate')}</div>
              <div className={`text-4xl font-bold tabular-nums ${
                data.win_rate.win_pct >= 60 ? 'text-emerald-400' :
                data.win_rate.win_pct >= 50 ? 'text-amber-400' : 'text-red-400'
              }`}>{data.win_rate.win_pct}%</div>
              <div className="text-xs text-zinc-500 mt-1">
                {t('player.wlDraws', { w: data.win_rate.wins, l: data.win_rate.losses, dPart: data.win_rate.draws > 0 ? ` / ${data.win_rate.draws}D` : '', total: data.win_rate.total })}
              </div>
            </div>
            <div>
              <div className="text-xs text-blue-400 uppercase tracking-widest mb-1">🟦 {t('player.asAllies')}</div>
              {data.win_rate.allies_total > 0 ? (
                <>
                  <div className="text-2xl font-bold text-blue-300 tabular-nums">{data.win_rate.allies_win_pct}%</div>
                  <div className="text-xs text-zinc-500">{t('player.winsOf', { w: data.win_rate.allies_wins, t: data.win_rate.allies_total })}</div>
                  <div className="h-1.5 bg-zinc-800 rounded mt-2 overflow-hidden">
                    <div className="bg-blue-500 h-full" style={{ width: `${data.win_rate.allies_win_pct}%` }} />
                  </div>
                </>
              ) : <div className="text-zinc-600 text-sm">{t('records.noData')}</div>}
            </div>
            <div>
              <div className="text-xs text-red-400 uppercase tracking-widest mb-1">🟥 {t('player.asAxis')}</div>
              {data.win_rate.axis_total > 0 ? (
                <>
                  <div className="text-2xl font-bold text-red-300 tabular-nums">{data.win_rate.axis_win_pct}%</div>
                  <div className="text-xs text-zinc-500">{t('player.winsOf', { w: data.win_rate.axis_wins, t: data.win_rate.axis_total })}</div>
                  <div className="h-1.5 bg-zinc-800 rounded mt-2 overflow-hidden">
                    <div className="bg-red-500 h-full" style={{ width: `${data.win_rate.axis_win_pct}%` }} />
                  </div>
                </>
              ) : <div className="text-zinc-600 text-sm">{t('records.noData')}</div>}
            </div>
          </div>
          <div className="text-xs text-zinc-600 mt-3 text-center">
            {t('player.winRateBasis')}
          </div>
        </section>
      )}

      {/* Radar + progression sparkline */}
      <section className="mb-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4">
          <div className="text-xs text-zinc-500 uppercase tracking-widest mb-2 text-center">⭐ {t('player.playstyle')}</div>
          <PlayerRadar p={p} />
        </div>
        <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4 flex flex-col">
          <div className="text-xs text-zinc-500 uppercase tracking-widest mb-2">📈 {t('player.kdTrend')}</div>
          <div className="flex-1">
            <ProgressionSparkline matches={data.recent_matches} />
          </div>
          <div className="text-xs text-zinc-600 text-center mt-1">{t('player.dashedLine')}</div>
        </div>
      </section>

      {/* Kill / death type breakdown + melee callout */}
      <section className="mb-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4">
          <ClassBreakdownBar counts={data.kills_by_class} title={`🔫 ${t('player.killsByWeaponClass')}`} />
        </div>
        <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4">
          <ClassBreakdownBar counts={data.deaths_by_class} title={`💀 ${t('player.deathsByWeaponClass')}`} />
        </div>
      </section>

      {(data.kills_by_class.Melee || data.deaths_by_class.Melee) && (
        <section className="mb-6 bg-gradient-to-r from-violet-900/30 via-zinc-900 to-rose-900/30 border border-violet-700/40 rounded-lg p-4">
          <h2 className="text-violet-300 uppercase text-xs tracking-widest mb-2">🔪 {t('player.melee')}</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-violet-300 tabular-nums">{data.kills_by_class.Melee ?? 0}</div>
              <div className="text-xs text-zinc-500">{t('player.meleeKilled')}</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-rose-300 tabular-nums">{data.deaths_by_class.Melee ?? 0}</div>
              <div className="text-xs text-zinc-500">{t('player.meleeDied')}</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-amber-300 tabular-nums">{data.melee_meta?.current_streak ?? 0}</div>
              <div className="text-xs text-zinc-500">{t('player.meleeStreak')}</div>
            </div>
            <div>
              {data.melee_meta?.last_melee_death ? (
                <>
                  <div className="text-sm text-zinc-300 truncate" title={data.melee_meta.last_melee_death.weapon}>
                    {data.melee_meta.last_melee_death.weapon}
                  </div>
                  <div className="text-xs text-zinc-500 mt-1">
                    {t('player.lastMeleeDeath')}
                    {data.melee_meta.last_melee_death.event_time && (
                      <> • {new Date(data.melee_meta.last_melee_death.event_time).toLocaleDateString(lang)}</>
                    )}
                  </div>
                  {data.melee_meta.last_melee_death.killer_sid && data.melee_meta.last_melee_death.killer_name && (
                    <Link
                      to={`/player/${data.melee_meta.last_melee_death.killer_sid}`}
                      className="text-xs text-rose-300 hover:underline"
                    >→ {data.melee_meta.last_melee_death.killer_name}</Link>
                  )}
                </>
              ) : (
                <>
                  <div className="text-2xl font-bold text-emerald-300">∞</div>
                  <div className="text-xs text-zinc-500">{t('player.noMeleeDeath')}</div>
                </>
              )}
            </div>
          </div>
        </section>
      )}

      <SectionDivider label={`⚔ ${t('player.pvpSection')}`} />

      {/* Nemesis stamp — top killer highlighted as eternal rival */}
      <NemesisStamp d={data} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {/* PVP: most killed */}
        <section>
          <h2 className="text-amber-400 uppercase text-xs tracking-widest mb-3">
            🎯 {t('player.topVictims')}
          </h2>
          <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4 space-y-2">
            {data.most_killed.length === 0 && <div className="text-zinc-600 text-sm">{t('records.noData')}</div>}
            {data.most_killed.map((v) => {
              // Weapon breakdown for this victim, from log_lines (only logged
              // matches). Match by name — most_killed lacks the FK we'd need
              // for sid-level join, and the log entry name is the same denorm
              // string. Total in pvp_breakdown can be ≤ v.kills because of
              // matches without log coverage; we just show what's logged.
              const breakdown = data.pvp_breakdown?.victims.find(
                (b) => b.victim_name === v.victim,
              )
              return (
                <div key={v.victim}>
                  <BarRow name={v.victim} value={v.kills} max={maxKilled}
                    color="bg-gradient-to-r from-green-700 to-green-500"
                    onClick={() => handlePvpClick(v.victim)} />
                  <WeaponSubline weapons={breakdown?.weapons ?? []} accent="green" />
                </div>
              )
            })}
          </div>
        </section>

        {/* PVP: killers */}
        <section>
          <h2 className="text-red-400 uppercase text-xs tracking-widest mb-3">
            💀 {t('player.worstKillers')}
          </h2>
          <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4 space-y-2">
            {data.killed_by.length === 0 && <div className="text-zinc-600 text-sm">{t('records.noData')}</div>}
            {data.killed_by.map((k) => {
              const breakdown = data.pvp_breakdown?.killers.find(
                (b) => b.killer_name === k.killer,
              )
              return (
                <div key={k.killer}>
                  <BarRow name={k.killer} value={k.deaths} max={maxKillers}
                    color="bg-gradient-to-r from-red-700 to-red-500"
                    onClick={() => handlePvpClick(k.killer)} />
                  <WeaponSubline weapons={breakdown?.weapons ?? []} accent="red" />
                </div>
              )
            })}
          </div>
        </section>

        {/* Weapons */}
        <section>
          <h2 className="text-blue-400 uppercase text-xs tracking-widest mb-3">
            🔫 {t('player.favWeapon')}
          </h2>
          <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4 space-y-2">
            {data.top_weapons.length === 0 && <div className="text-zinc-600 text-sm">{t('records.noData')}</div>}
            {data.top_weapons.map((w) => (
              <BarRow key={w.weapon} name={w.weapon} value={w.kills} max={maxWeapon}
                color="bg-gradient-to-r from-blue-700 to-blue-500" />
            ))}
          </div>
        </section>
      </div>

      {/* Hardcounters — players with positive K/D against this player.
          Snarky banner: "ці гравці регулярно тебе перегравають". */}
      {data.hardcounters && data.hardcounters.length > 0 && (
        <section className="mb-6 bg-gradient-to-r from-zinc-900 via-rose-950/30 to-zinc-900 border border-rose-900/40 rounded-lg p-4">
          <h2 className="text-rose-300 uppercase text-xs tracking-widest mb-3">
            🥊 {t('player.hardcounters')}
          </h2>
          <ol className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-2 text-sm">
            {data.hardcounters.map((h, i) => (
              <li key={h.steam_id} className="flex items-center gap-2 bg-zinc-900/60 rounded p-2 border border-zinc-800">
                <span className="text-zinc-500 w-5 text-right">{i + 1}.</span>
                <Link to={`/player/${h.steam_id}`} className="flex-1 truncate hover:text-rose-300 transition-colors font-medium" title={h.name}>
                  {h.name}
                </Link>
                <MiniCompareButton steam_id={h.steam_id} name={h.name} />
                <span className="text-xs text-zinc-400 tabular-nums whitespace-nowrap" title={t('player.killedVsRevenged', { killed: h.killed_me, revenged: h.i_killed_them })}>
                  <span className="text-red-400">{h.killed_me}</span>
                  <span className="text-zinc-600">/</span>
                  <span className="text-green-400">{h.i_killed_them}</span>
                </span>
                <span className="text-xs text-rose-400 font-bold tabular-nums" title={t('player.advantage')}>+{h.advantage}</span>
              </li>
            ))}
          </ol>
        </section>
      )}

      {/* Most played with / against — co-presence in logged matches */}
      {(data.played_with_against?.teammates?.length || data.played_with_against?.opponents?.length) && (
        <section className="mb-6 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4">
            <h2 className="text-emerald-400 uppercase text-xs tracking-widest mb-3">🤝 {t('player.topTeammates')}</h2>
            <ol className="space-y-1 text-sm">
              {data.played_with_against.teammates.map((tm, i) => (
                <li key={tm.steam_id} className="flex items-baseline gap-2">
                  <span className="text-zinc-500 w-5 text-right">{i + 1}.</span>
                  <Link to={`/player/${tm.steam_id}`} className="flex-1 truncate hover:text-emerald-300 transition-colors" title={tm.name}>{tm.name}</Link>
                  <MiniCompareButton steam_id={tm.steam_id} name={tm.name} />
                  <span className="text-zinc-300 tabular-nums">{tm.matches}</span>
                </li>
              ))}
              {data.played_with_against.teammates.length === 0 && (
                <li className="text-zinc-600 text-xs italic">{t('player.noDataLogs')}</li>
              )}
            </ol>
          </div>
          <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4">
            <h2 className="text-rose-400 uppercase text-xs tracking-widest mb-3">⚔ {t('player.topOpponents')}</h2>
            <ol className="space-y-1 text-sm">
              {data.played_with_against.opponents.map((op, i) => (
                <li key={op.steam_id} className="flex items-baseline gap-2">
                  <span className="text-zinc-500 w-5 text-right">{i + 1}.</span>
                  <Link to={`/player/${op.steam_id}`} className="flex-1 truncate hover:text-rose-300 transition-colors" title={op.name}>{op.name}</Link>
                  <MiniCompareButton steam_id={op.steam_id} name={op.name} />
                  <span className="text-zinc-300 tabular-nums">{op.matches}</span>
                </li>
              ))}
              {data.played_with_against.opponents.length === 0 && (
                <li className="text-zinc-600 text-xs italic">{t('player.noDataLogs')}</li>
              )}
            </ol>
          </div>
        </section>
      )}

      <SectionDivider label={`🗺 ${t('player.activityHistory')}`} />

      {/* Loved / Hated map cards — best vs worst K/D among top played maps */}
      <LovedHatedMap topMaps={data.top_maps ?? []} />

      {/* Top maps table */}
      {data.top_maps && data.top_maps.length > 0 && (
        <section className="mb-6">
          <h2 className="text-zinc-300 uppercase text-xs tracking-widest mb-3">🗺 {t('player.top10Maps')}</h2>
          <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-zinc-800 text-zinc-400 text-xs uppercase">
                <tr>
                  <th className="p-2 text-left">{t('filters.map')}</th>
                  <th className="p-2 text-right">{t('table.matches')}</th>
                  <th className="p-2 text-right">{t('table.kills')}</th>
                  <th className="p-2 text-right">{t('table.kd')}</th>
                  <th className="p-2 text-right" title={t('player.winPctTooltip')}>{t('player.winPct')}</th>
                </tr>
              </thead>
              <tbody>
                {data.top_maps.map((m) => (
                  <tr key={m.map_name} className="border-t border-zinc-800">
                    <td className="p-2" title={m.map_name}>{formatMapName(m.map_name)}</td>
                    <td className="p-2 text-right tabular-nums">{m.matches}</td>
                    <td className="p-2 text-right tabular-nums text-green-400">{m.kills != null ? nf.format(m.kills) : '—'}</td>
                    <td className="p-2 text-right tabular-nums">{m.kd ?? '—'}</td>
                    <td className="p-2 text-right tabular-nums">
                      {m.win_pct !== null ? (
                        <span className={
                          m.win_pct >= 65 ? 'text-emerald-400' :
                          m.win_pct >= 50 ? 'text-amber-400' :
                          m.win_pct >= 35 ? 'text-orange-400' : 'text-red-400'
                        } title={t('player.winOf', { pct: m.win_pct, n: m.known_outcomes })}>
                          {m.win_pct}%
                        </span>
                      ) : <span className="text-zinc-600" title={t('player.noLogCoverageShort')}>—</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Time-of-day heatmap */}
      <section className="mt-6 bg-zinc-900/60 border border-zinc-800 rounded-lg p-4">
        <h2 className="text-zinc-300 uppercase text-xs tracking-widest mb-3">
          🕐 {t('player.whenPlays')}
        </h2>
        <TimeOfDayHeatmap hours={data.hour_distribution ?? []} />
      </section>

      {/* Recent matches — tab between all / titled-only */}
      {(() => {
        const titledMatches = data.recent_matches.filter((m) => matchTitle({
          kills: m.kills, deaths: m.deaths, kd: m.kd,
          combat: m.combat, support: m.support, map_name: m.map_name,
          time_seconds: m.time_seconds,
        }) !== null)
        const visibleMatches = recentFilter === 'titled'
          ? titledMatches
          : data.recent_matches.slice(0, 10)
        const tabCls = (active: boolean) =>
          `px-3 py-1.5 text-xs uppercase tracking-widest rounded-t border-b-2 transition-colors ${
            active ? 'text-amber-400 border-amber-500' : 'text-zinc-500 border-transparent hover:text-zinc-300'
          }`
        return (
          <section className="mt-6">
            <div className="flex items-center gap-1 mb-3 border-b border-zinc-800">
              <button onClick={() => setRecentFilter('all')} className={tabCls(recentFilter === 'all')}>
                {t('player.recentMatches', { n: Math.min(10, data.recent_matches.length) })}
              </button>
              <button onClick={() => setRecentFilter('titled')} className={tabCls(recentFilter === 'titled')}>
                🏷 {t('player.withTitles', { n: titledMatches.length })}
              </button>
            </div>
            <div className="overflow-x-auto bg-zinc-900/40 border border-zinc-800 rounded-lg">
              <table className="w-full text-sm">
                <thead className="bg-zinc-800 text-zinc-300 text-xs uppercase">
                  <tr>
                    <th className="p-3 text-left">{t('player.date')}</th>
                    <th className="p-3 text-left">{t('filters.map')}</th>
                    <th className="p-3 text-right" title={t('player.timePctTooltip')}>{t('player.timePct')}</th>
                    <th className="p-3 text-right">K</th>
                    <th className="p-3 text-right">D</th>
                    <th className="p-3 text-right">K/D</th>
                    <th className="p-3 text-right">Combat</th>
                    <th className="p-3 text-right">Support</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleMatches.length === 0 && (
                    <tr><td colSpan={8} className="p-4 text-center text-zinc-600 italic">
                      {recentFilter === 'titled' ? t('player.noTitledMatches') : t('player.noMatches')}
                    </td></tr>
                  )}
                  {visibleMatches.map((m, i) => (
                <tr key={i} className="border-t border-zinc-800 hover:bg-zinc-800/40">
                  <td className="p-3 text-zinc-400 text-xs whitespace-nowrap">
                    {m.match_date ? new Date(m.match_date).toLocaleDateString(lang) : '—'}
                  </td>
                  <td className="p-3">
                    <a
                      href={`${CRCON_PUBLIC_BASE}/games/${m.match_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-amber-400 hover:text-amber-300 hover:underline"
                      title={t('player.openMatchInCrcon', { map: m.map_name })}
                    >
                      {formatMapName(m.map_name)}
                    </a>
                    {(() => {
                      const t = matchTitle({
                        kills: m.kills, deaths: m.deaths, kd: m.kd,
                        combat: m.combat, support: m.support, map_name: m.map_name,
                        time_seconds: m.time_seconds,
                      })
                      return t ? (
                        <Link
                          to="/match-titles"
                          className="ml-2 text-xs px-1.5 py-0.5 rounded bg-amber-900/40 border border-amber-700/40 text-amber-200 hover:bg-amber-800/50"
                          title={t.description}
                        >
                          {t.emoji} {t.title}
                        </Link>
                      ) : null
                    })()}
                  </td>
                  <td className="p-3 text-right tabular-nums text-zinc-400 text-xs">
                    {m.time_pct !== null && m.time_pct !== undefined ? (
                      <span className={m.time_pct >= 80 ? 'text-zinc-300' : m.time_pct >= 50 ? 'text-amber-400' : 'text-zinc-500'}
                        title={t('player.minutes', { n: Math.floor((m.time_seconds || 0) / 60) })}>
                        {m.time_pct}%
                      </span>
                    ) : '—'}
                  </td>
                  <td className="p-3 text-right text-green-400">{m.kills}</td>
                  <td className="p-3 text-right text-red-400">{m.deaths}</td>
                  <td className="p-3 text-right">{m.kd?.toFixed?.(2) ?? '—'}</td>
                  <td className="p-3 text-right">{m.combat}</td>
                  <td className="p-3 text-right">{m.support}</td>
                </tr>
              ))}
                </tbody>
              </table>
            </div>
          </section>
        )
      })()}
    </div>
  )
}
