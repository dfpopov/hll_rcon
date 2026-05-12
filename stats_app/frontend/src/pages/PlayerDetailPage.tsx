import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { fetchPlayerDetail, findPlayerByName, PlayerDetail } from '../api/client'
import { useCompareList } from '../hooks/useCompareList'
import LevelBadge from '../components/LevelBadge'
import Avatar from '../components/Avatar'
import AchievementBadge from '../components/AchievementBadge'
import CountryFlag from '../components/CountryFlag'

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

function AddToCompareButton({ steam_id, name }: { steam_id: string; name: string }) {
  const { has, add, remove, list, max } = useCompareList()
  const inList = has(steam_id)
  const full = !inList && list.length >= max

  const onClick = () => {
    if (inList) {
      remove(steam_id)
    } else {
      const result = add({ steam_id, name })
      if (result === 'full') alert(`Список порівняння вже містить максимум ${max} гравців.`)
    }
  }

  const label = inList
    ? '✓ У списку порівняння'
    : full
      ? `Список заповнений (${max})`
      : '➕ Додати до порівняння'
  const cls = inList
    ? 'bg-amber-700/40 text-amber-200 border-amber-600/50'
    : full
      ? 'bg-zinc-800 text-zinc-500 border-transparent cursor-not-allowed'
      : 'bg-zinc-800 hover:bg-zinc-700 text-amber-400 hover:text-amber-300 border-transparent'

  return (
    <button onClick={onClick} disabled={full}
      className={`text-xs px-3 py-1 rounded border ${cls}`}
      title={inList ? 'Прибрати зі списку' : full ? 'Прибери когось зі списку щоб додати' : 'Додати до порівняння'}>
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

function BarRow({ name, value, max, color, onClick }: {
  name: string; value: number; max: number; color: string; onClick?: () => void
}) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0
  return (
    <div className="flex items-center gap-2 text-sm">
      <span
        className={`w-44 truncate ${onClick ? 'cursor-pointer hover:text-amber-400 transition-colors' : ''}`}
        title={onClick ? `${name} — клікніть для профілю` : name}
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
  const { steamId } = useParams<{ steamId: string }>()
  const navigate = useNavigate()
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
             className="text-xs text-amber-400 hover:text-amber-300 px-3 py-1 rounded bg-zinc-800 hover:bg-zinc-700">
            Steam ↗
          </a>
        )}
        <AddToCompareButton steam_id={p.steam_id} name={p.name} />
      </div>

      {/* Achievements row */}
      {data.achievements && data.achievements.length > 0 && (
        <section className="mb-6">
          <h2 className="text-zinc-300 uppercase text-xs tracking-widest mb-2">
            Досягнення ({data.achievements.length})
          </h2>
          <div className="flex flex-wrap gap-2">
            {data.achievements.map((a) => (
              <AchievementBadge key={a.id} a={a} />
            ))}
          </div>
        </section>
      )}

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

      {/* Profile overview: first seen, 100+ kill matches, faction & mode preference */}
      <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        <div className="bg-zinc-900/60 border border-zinc-800 rounded p-3">
          <div className="text-xs text-zinc-500 uppercase tracking-widest">Перший матч</div>
          <div className="text-base font-medium mt-1">
            {data.overview.first_seen
              ? new Date(data.overview.first_seen).toLocaleDateString('uk-UA', { year: 'numeric', month: 'short', day: 'numeric' })
              : '—'}
          </div>
          <div className="text-xs text-zinc-500 mt-1">{data.overview.total_matches} матчів усього</div>
        </div>

        <div className="bg-zinc-900/60 border border-zinc-800 rounded p-3">
          <div className="text-xs text-zinc-500 uppercase tracking-widest">100+ kill матчів</div>
          <div className="text-2xl font-bold mt-1 tabular-nums text-emerald-400">{data.overview.matches_100plus}</div>
          <div className="text-xs text-zinc-500 mt-1">
            {data.overview.total_matches > 0
              ? `${(data.overview.matches_100plus / data.overview.total_matches * 100).toFixed(2)}% усіх ігор`
              : '—'}
          </div>
        </div>

        {/* Game mode preference */}
        <div className="bg-zinc-900/60 border border-zinc-800 rounded p-3">
          <div className="text-xs text-zinc-500 uppercase tracking-widest mb-2">Режими</div>
          {(() => {
            const m = data.overview.mode_counts
            const total = m.warfare + m.offensive + m.skirmish
            if (total === 0) return <div className="text-zinc-600 text-sm">немає даних</div>
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
            Сторона <span className="text-zinc-600 normal-case">(з логів)</span>
          </div>
          {data.faction_pref.total_known === 0 ? (
            <div className="text-zinc-600 text-sm">матчі без лог-покриття</div>
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
              <div className="text-xs text-zinc-500 mt-1">з {data.faction_pref.total_known} відомих матчів</div>
            </>
          )}
        </div>
      </section>

      {/* Kill / death type breakdown + melee callout */}
      <section className="mb-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4">
          <ClassBreakdownBar counts={data.kills_by_class} title="🔫 Вбивства за типом зброї" />
        </div>
        <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4">
          <ClassBreakdownBar counts={data.deaths_by_class} title="💀 Смерті за типом зброї" />
        </div>
      </section>

      {(data.kills_by_class.Melee || data.deaths_by_class.Melee) && (
        <section className="mb-6 bg-gradient-to-r from-violet-900/30 via-zinc-900 to-rose-900/30 border border-violet-700/40 rounded-lg p-4">
          <h2 className="text-violet-300 uppercase text-xs tracking-widest mb-2">🔪 Ближній бій</h2>
          <div className="grid grid-cols-2 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-violet-300 tabular-nums">{data.kills_by_class.Melee ?? 0}</div>
              <div className="text-xs text-zinc-500">вбито в ближньому бою</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-rose-300 tabular-nums">{data.deaths_by_class.Melee ?? 0}</div>
              <div className="text-xs text-zinc-500">загинуло від ближнього бою</div>
            </div>
          </div>
        </section>
      )}

      {/* Top maps */}
      {data.top_maps && data.top_maps.length > 0 && (
        <section className="mb-6">
          <h2 className="text-zinc-300 uppercase text-xs tracking-widest mb-3">🗺 Топ-10 карт за матчами</h2>
          <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-zinc-800 text-zinc-400 text-xs uppercase">
                <tr>
                  <th className="p-2 text-left">Карта</th>
                  <th className="p-2 text-right">Матчів</th>
                  <th className="p-2 text-right">Kills</th>
                  <th className="p-2 text-right">K/D</th>
                </tr>
              </thead>
              <tbody>
                {data.top_maps.map((m) => (
                  <tr key={m.map_name} className="border-t border-zinc-800">
                    <td className="p-2">{m.map_name}</td>
                    <td className="p-2 text-right tabular-nums">{m.matches}</td>
                    <td className="p-2 text-right tabular-nums text-green-400">{m.kills?.toLocaleString('uk-UA') ?? '—'}</td>
                    <td className="p-2 text-right tabular-nums">{m.kd ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Top servers */}
      {data.top_servers && data.top_servers.length > 0 && (
        <section className="mb-6">
          <h2 className="text-zinc-300 uppercase text-xs tracking-widest mb-3">🖥 Найчастіші сервери</h2>
          <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-zinc-800 text-zinc-400 text-xs uppercase">
                <tr>
                  <th className="p-2 text-left">Сервер</th>
                  <th className="p-2 text-right">Сесій</th>
                  <th className="p-2 text-right">Годин</th>
                </tr>
              </thead>
              <tbody>
                {data.top_servers.map((s) => (
                  <tr key={s.server_name} className="border-t border-zinc-800">
                    <td className="p-2 truncate">{s.server_name}</td>
                    <td className="p-2 text-right tabular-nums">{s.sessions}</td>
                    <td className="p-2 text-right tabular-nums">{Math.floor(s.total_seconds / 3600)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

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
                color="bg-gradient-to-r from-green-700 to-green-500"
                onClick={() => handlePvpClick(v.victim)} />
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
                color="bg-gradient-to-r from-red-700 to-red-500"
                onClick={() => handlePvpClick(k.killer)} />
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
                <tr key={i} className="border-t border-zinc-800 hover:bg-zinc-800/40">
                  <td className="p-3 text-zinc-400 text-xs whitespace-nowrap">
                    {m.match_date ? new Date(m.match_date).toLocaleDateString('uk-UA') : '—'}
                  </td>
                  <td className="p-3">
                    <a
                      href={`${CRCON_PUBLIC_BASE}/games/${m.match_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-amber-400 hover:text-amber-300 hover:underline"
                      title="Відкрити деталі матчу в CRCON ↗"
                    >
                      {m.map_name}
                    </a>
                  </td>
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
