import { useEffect, useMemo, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import {
  fetchPlayerDetail, fetchHeadToHead, findPlayerByName,
  HeadToHead, PlayerDetail, PlayerProfile,
} from '../api/client'
import { useCompareList } from '../hooks/useCompareList'
import LevelBadge from '../components/LevelBadge'
import Avatar from '../components/Avatar'
import CountryFlag from '../components/CountryFlag'
import AchievementBadge from '../components/AchievementBadge'

function fmt(v: number | null | undefined): string {
  if (v == null) return '—'
  if (Math.abs(v) >= 10000) return v.toLocaleString('uk-UA')
  return String(v)
}

function pairColor(a: number, b: number, higherBetter = true): string {
  if (a === b) return 'text-zinc-400'
  const aWins = higherBetter ? a > b : a < b
  return aWins ? 'text-green-400' : 'text-red-400'
}

/** For N≥3: max gets green, min gets red, middle neutral. */
function multiColor(value: number, all: number[], higherBetter = true): string {
  if (value == null) return 'text-zinc-500'
  const max = Math.max(...all)
  const min = Math.min(...all)
  if (max === min) return 'text-zinc-300'
  const isMax = value === max
  const isMin = value === min
  const winner = higherBetter ? isMax : isMin
  const loser  = higherBetter ? isMin : isMax
  if (winner) return 'text-green-400 font-bold'
  if (loser)  return 'text-red-400'
  return 'text-zinc-300'
}

// Stat rows for the comparison table — shared by 1v1 (paired) and Nv view.
interface StatDef {
  label: string
  get: (p: PlayerProfile) => number
  higherBetter?: boolean
}
const STAT_ROWS: StatDef[] = [
  { label: 'Level',              get: (p) => p.level },
  { label: 'Kills',              get: (p) => p.kills },
  { label: 'Deaths',             get: (p) => p.deaths, higherBetter: false },
  { label: 'K/D',                get: (p) => p.kd_ratio ?? 0 },
  { label: 'KPM',                get: (p) => p.kpm ?? 0 },
  { label: 'Матчів',             get: (p) => p.matches_played },
  { label: 'Годин',              get: (p) => Math.floor(p.total_seconds / 3600) },
  { label: 'Combat',             get: (p) => p.combat },
  { label: 'Offense',            get: (p) => p.offense },
  { label: 'Defense',            get: (p) => p.defense },
  { label: 'Support',            get: (p) => p.support },
  { label: 'Best streak',        get: (p) => p.best_kills_streak },
  { label: 'Найдовше життя (с)', get: (p) => p.longest_life_secs },
  { label: 'Team kills',         get: (p) => p.teamkills, higherBetter: false },
  { label: 'Смертей від ТК',     get: (p) => p.deaths_by_tk, higherBetter: false },
]

function PlayerHeader({ p, large = false }: { p: PlayerProfile; large?: boolean }) {
  return (
    <div className="text-center">
      <div className="flex justify-center mb-2">
        <Avatar url={p.avatar_url} name={p.name} size={large ? 64 : 48} />
      </div>
      <div className="flex justify-center items-center gap-2 mb-1">
        <LevelBadge level={p.level} size={large ? 'md' : 'sm'} />
        <CountryFlag iso={p.country} />
      </div>
      <div className={`font-bold break-all ${large ? 'text-lg' : 'text-sm'}`}>{p.name}</div>
      <Link to={`/player/${p.steam_id}`} className="text-xs text-amber-400 hover:underline">
        Профіль ↗
      </Link>
    </div>
  )
}

// ─────────────────────────── 1v1 rich layout ───────────────────────────

function RichCompareView({ d1, d2, h2h }: { d1: PlayerDetail; d2: PlayerDetail; h2h: HeadToHead | null }) {
  const p1 = d1.profile, p2 = d2.profile

  return (
    <>
      <div className="grid grid-cols-2 gap-8 mb-6">
        <PlayerHeader p={p1} large />
        <PlayerHeader p={p2} large />
      </div>

      {h2h && (h2h.p1_killed_p2 > 0 || h2h.p2_killed_p1 > 0) ? (
        <div className="bg-gradient-to-r from-zinc-900 via-zinc-800/80 to-zinc-900 border border-amber-700/40 rounded-lg p-4 mb-6">
          <h2 className="text-amber-400 text-xs uppercase tracking-widest mb-3 text-center">
            ⚔ Особистий рахунок
          </h2>
          <div className="grid grid-cols-3 items-center gap-2 text-center">
            <div>
              <div className="text-3xl font-bold text-green-400 tabular-nums">{h2h.p1_killed_p2}</div>
              <div className="text-xs text-zinc-400 mt-1">
                <span className="font-medium">{p1.name}</span> вбив <span className="font-medium">{p2.name}</span>
              </div>
              {h2h.p1_top_weapon && (
                <div className="text-xs text-zinc-500 mt-1">улюблена зброя: <span className="text-zinc-300">{h2h.p1_top_weapon}</span></div>
              )}
            </div>
            <div className="text-2xl text-zinc-600">vs</div>
            <div>
              <div className="text-3xl font-bold text-red-400 tabular-nums">{h2h.p2_killed_p1}</div>
              <div className="text-xs text-zinc-400 mt-1">
                <span className="font-medium">{p2.name}</span> вбив <span className="font-medium">{p1.name}</span>
              </div>
              {h2h.p2_top_weapon && (
                <div className="text-xs text-zinc-500 mt-1">улюблена зброя: <span className="text-zinc-300">{h2h.p2_top_weapon}</span></div>
              )}
            </div>
          </div>
          {h2h.p1_killed_p2 !== h2h.p2_killed_p1 && (
            <div className="text-center text-xs text-zinc-500 mt-3">
              {h2h.p1_killed_p2 > h2h.p2_killed_p1
                ? `${p1.name} домінує (+${h2h.p1_killed_p2 - h2h.p2_killed_p1})`
                : `${p2.name} домінує (+${h2h.p2_killed_p1 - h2h.p1_killed_p2})`}
            </div>
          )}
        </div>
      ) : h2h && (
        <div className="bg-zinc-900/40 border border-zinc-800 rounded-lg p-3 mb-6 text-center text-zinc-500 text-sm">
          🤝 Не зустрічались на полі бою (за наявністю логів)
        </div>
      )}

      <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg overflow-hidden mb-6">
        <table className="w-full text-sm">
          <tbody>
            {STAT_ROWS.map((s) => (
              <tr key={s.label} className="border-t border-zinc-800">
                <td className={`p-3 text-right font-medium tabular-nums ${pairColor(s.get(p1), s.get(p2), s.higherBetter)}`}>
                  {fmt(s.get(p1))}
                </td>
                <td className="p-3 text-center text-zinc-500 text-xs uppercase">{s.label}</td>
                <td className={`p-3 text-left font-medium tabular-nums ${pairColor(s.get(p2), s.get(p1), s.higherBetter)}`}>
                  {fmt(s.get(p2))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4 mb-6">
        <h2 className="text-zinc-300 uppercase text-xs tracking-widest mb-3 text-center">🔫 Топ-3 зброя</h2>
        <div className="grid grid-cols-2 gap-6">
          {[d1, d2].map((d, idx) => (
            <ol key={idx} className="space-y-1 text-sm">
              {d.top_weapons.slice(0, 3).map((w, i) => (
                <li key={w.weapon} className="flex items-baseline gap-2">
                  <span className="text-zinc-500 w-5 text-right">{i + 1}.</span>
                  <span className="flex-1 truncate" title={w.weapon}>{w.weapon}</span>
                  <span className="text-zinc-200 tabular-nums font-medium">{w.kills.toLocaleString('uk-UA')}</span>
                </li>
              ))}
              {d.top_weapons.length === 0 && <li className="text-zinc-600 text-xs italic">немає даних</li>}
            </ol>
          ))}
        </div>
      </div>

      <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4">
        <h2 className="text-zinc-300 uppercase text-xs tracking-widest mb-3 text-center">
          🏅 Досягнення ({d1.achievements.length} vs {d2.achievements.length})
        </h2>
        <div className="grid grid-cols-2 gap-6">
          {[d1, d2].map((d, idx) => (
            <div key={idx} className="flex flex-wrap gap-1.5">
              {d.achievements.map((a) => <AchievementBadge key={a.id} a={a} />)}
              {d.achievements.length === 0 && <div className="text-zinc-600 text-xs italic">немає досягнень</div>}
            </div>
          ))}
        </div>
      </div>
    </>
  )
}

// ─────────────────────────── Nv compact layout (N=3..4) ───────────────────────────

function CompactCompareView({ details }: { details: PlayerDetail[] }) {
  return (
    <>
      <div className={`grid gap-4 mb-6`}
        style={{ gridTemplateColumns: `repeat(${details.length}, minmax(0, 1fr))` }}
      >
        {details.map((d) => <PlayerHeader key={d.profile.steam_id} p={d.profile} />)}
      </div>

      <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg overflow-hidden mb-6">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-zinc-800 text-zinc-300 text-xs uppercase">
              <th className="p-3 text-left">Метрика</th>
              {details.map((d) => (
                <th key={d.profile.steam_id} className="p-3 text-center">
                  <span className="truncate inline-block max-w-[140px]" title={d.profile.name}>{d.profile.name}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {STAT_ROWS.map((row) => {
              const values = details.map((d) => row.get(d.profile))
              return (
                <tr key={row.label} className="border-t border-zinc-800">
                  <td className="p-3 text-zinc-400 text-xs uppercase">{row.label}</td>
                  {details.map((d, i) => (
                    <td
                      key={d.profile.steam_id}
                      className={`p-3 text-center tabular-nums ${multiColor(values[i], values, row.higherBetter)}`}
                    >
                      {fmt(values[i])}
                    </td>
                  ))}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4">
        <h2 className="text-zinc-300 uppercase text-xs tracking-widest mb-3 text-center">🏅 Досягнення</h2>
        <div className={`grid gap-4`}
          style={{ gridTemplateColumns: `repeat(${details.length}, minmax(0, 1fr))` }}
        >
          {details.map((d) => (
            <div key={d.profile.steam_id} className="flex flex-wrap gap-1.5 justify-center">
              <span className="w-full text-center text-xs text-zinc-500">{d.profile.name}: {d.achievements.length}</span>
              {d.achievements.map((a) => <AchievementBadge key={a.id} a={a} />)}
              {d.achievements.length === 0 && <span className="text-zinc-600 text-xs italic">немає</span>}
            </div>
          ))}
        </div>
      </div>
    </>
  )
}

// ─────────────────────────── No-ids landing ───────────────────────────

function LandingView({ initialName1 = '' }: { initialName1?: string }) {
  const navigate = useNavigate()
  const { list } = useCompareList()
  const [name1, setName1] = useState(initialName1)
  const [name2, setName2] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleCompare = async () => {
    if (!name1 || !name2) return
    setSubmitting(true)
    const [s1, s2] = await Promise.all([findPlayerByName(name1), findPlayerByName(name2)])
    setSubmitting(false)
    if (!s1 || !s2) {
      alert(`Не знайдено: ${!s1 ? name1 + ' ' : ''}${!s2 ? name2 : ''}`)
      return
    }
    navigate(`/compare/${encodeURIComponent(s1)},${encodeURIComponent(s2)}`)
  }

  const goFromList = () => {
    if (list.length < 2) return
    navigate(`/compare/${list.map((p) => encodeURIComponent(p.steam_id)).join(',')}`)
  }

  return (
    <div className="max-w-2xl mx-auto p-6">
      <header className="mb-6">
        <h1 className="text-3xl font-bold mb-1">Порівняння гравців</h1>
        <p className="text-zinc-400 text-sm">
          Додавайте гравців з їхніх профілів кнопкою «➕ Додати до порівняння» (до 4), або введіть імена напряму.
        </p>
      </header>

      {list.length >= 2 && (
        <div className="bg-amber-900/20 border border-amber-700/40 rounded-lg p-4 mb-4 flex items-center justify-between">
          <div>
            <div className="text-amber-300 font-medium text-sm">У вашому списку {list.length} гравців</div>
            <div className="text-zinc-400 text-xs mt-1">{list.map((p) => p.name).join(' • ')}</div>
          </div>
          <button
            onClick={goFromList}
            className="px-4 py-2 rounded bg-amber-600 hover:bg-amber-500 text-white font-medium text-sm"
          >
            Порівняти ({list.length})
          </button>
        </div>
      )}

      <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-6 space-y-4">
        <div className="text-zinc-400 text-xs uppercase tracking-widest">Швидке 1v1 за іменами</div>
        <div>
          <label className="block text-sm text-zinc-300 mb-1">Гравець 1</label>
          <input value={name1} onChange={(e) => setName1(e.target.value)}
            placeholder="Heartattack333" autoFocus
            className="w-full bg-zinc-800 text-zinc-100 px-3 py-2 rounded" />
        </div>
        <div>
          <label className="block text-sm text-zinc-300 mb-1">Гравець 2</label>
          <input value={name2} onChange={(e) => setName2(e.target.value)}
            placeholder="BaNnY"
            className="w-full bg-zinc-800 text-zinc-100 px-3 py-2 rounded" />
        </div>
        <button onClick={handleCompare} disabled={!name1 || !name2 || submitting}
          className="w-full px-4 py-2 rounded bg-amber-600 hover:bg-amber-500 text-white font-medium disabled:opacity-50">
          {submitting ? 'Шукаю…' : 'Порівняти 1v1'}
        </button>
      </div>
    </div>
  )
}

// ─────────────────────────── Page ───────────────────────────

export default function ComparePage() {
  const { ids: idsParam } = useParams<{ ids?: string }>()
  const ids = useMemo(
    () => (idsParam || '').split(',').map((s) => decodeURIComponent(s.trim())).filter(Boolean).slice(0, 4),
    [idsParam],
  )
  const [details, setDetails] = useState<PlayerDetail[]>([])
  const [h2h, setH2h] = useState<HeadToHead | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (ids.length < 2) { setDetails([]); setH2h(null); return }
    setLoading(true)
    setError(null)
    const detailsP = Promise.all(ids.map((id) => fetchPlayerDetail(id)))
    const h2hP = ids.length === 2
      ? fetchHeadToHead(ids[0], ids[1]).catch(() => null)
      : Promise.resolve(null)
    Promise.all([detailsP, h2hP])
      .then(([dets, hh]) => { setDetails(dets); setH2h(hh) })
      .catch((e) => setError(e?.response?.data?.detail ?? e?.message ?? 'error'))
      .finally(() => setLoading(false))
  }, [idsParam])  // eslint-disable-line react-hooks/exhaustive-deps

  if (ids.length === 0) return <LandingView />

  if (ids.length === 1) {
    return (
      <div className="max-w-3xl mx-auto p-6 text-center">
        <Link to="/compare" className="text-zinc-400 hover:text-amber-400 text-sm">← Порівняння</Link>
        <div className="mt-6 text-zinc-300">
          У порівнянні лише 1 гравець. Додайте ще {2 - ids.length}-3 з профілів кнопкою «➕ Додати до порівняння».
        </div>
      </div>
    )
  }

  if (loading) return <div className="text-zinc-400 p-6 text-center">Завантаження…</div>
  if (error || details.length === 0) return <div className="text-red-400 p-6">{error ?? 'не вдалось завантажити'}</div>

  return (
    <div className="max-w-6xl mx-auto p-6">
      <Link to="/compare" className="text-zinc-400 hover:text-amber-400 text-sm">← Інше порівняння</Link>
      <header className="my-6">
        <h1 className="text-3xl font-bold text-center">
          Порівняння {details.length === 2 ? 'гравців' : `${details.length} гравців`}
        </h1>
      </header>
      {details.length === 2
        ? <RichCompareView d1={details[0]} d2={details[1]} h2h={h2h} />
        : <CompactCompareView details={details} />}
    </div>
  )
}
