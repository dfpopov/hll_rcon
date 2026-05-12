import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { fetchPlayerDetail, fetchHeadToHead, findPlayerByName, HeadToHead, PlayerDetail } from '../api/client'
import LevelBadge from '../components/LevelBadge'
import Avatar from '../components/Avatar'
import CountryFlag from '../components/CountryFlag'
import AchievementBadge from '../components/AchievementBadge'

function fmt(v: number | null | undefined): string {
  if (v == null) return '—'
  if (Math.abs(v) >= 10000) return v.toLocaleString('uk-UA')
  return String(v)
}

function diffColor(a: number, b: number, higherBetter = true): string {
  if (a === b) return 'text-zinc-400'
  const aWins = higherBetter ? a > b : a < b
  return aWins ? 'text-green-400' : 'text-red-400'
}

function StatRow({ label, valA, valB, higherBetter = true }: {
  label: string; valA: number; valB: number; higherBetter?: boolean
}) {
  return (
    <tr className="border-t border-zinc-800">
      <td className={`p-3 text-right font-medium tabular-nums ${diffColor(valA, valB, higherBetter)}`}>
        {fmt(valA)}
      </td>
      <td className="p-3 text-center text-zinc-500 text-xs uppercase">{label}</td>
      <td className={`p-3 text-left font-medium tabular-nums ${diffColor(valB, valA, higherBetter)}`}>
        {fmt(valB)}
      </td>
    </tr>
  )
}

function PlayerHeader({ p }: { p: PlayerDetail['profile'] }) {
  return (
    <div className="text-center">
      <div className="flex justify-center mb-2">
        <Avatar url={p.avatar_url} name={p.name} size={64} />
      </div>
      <div className="flex justify-center items-center gap-2 mb-1">
        <LevelBadge level={p.level} size="sm" />
        <CountryFlag iso={p.country} />
      </div>
      <div className="text-lg font-bold break-all">{p.name}</div>
      <Link to={`/player/${p.steam_id}`} className="text-xs text-amber-400 hover:underline">
        Повний профіль ↗
      </Link>
    </div>
  )
}

export default function ComparePage() {
  const { id1, id2 } = useParams<{ id1?: string; id2?: string }>()
  const navigate = useNavigate()
  const [d1, setD1] = useState<PlayerDetail | null>(null)
  const [d2, setD2] = useState<PlayerDetail | null>(null)
  const [h2h, setH2h] = useState<HeadToHead | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Standalone search-and-compare form when no ids in URL
  const [name1, setName1] = useState('')
  const [name2, setName2] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!id1 || !id2) return
    setLoading(true)
    setError(null)
    Promise.all([
      fetchPlayerDetail(id1),
      fetchPlayerDetail(id2),
      fetchHeadToHead(id1, id2).catch(() => null),  // tolerant — h2h is bonus
    ])
      .then(([a, b, hh]) => { setD1(a); setD2(b); setH2h(hh) })
      .catch((e) => setError(e.message ?? 'error'))
      .finally(() => setLoading(false))
  }, [id1, id2])

  const handleCompare = async () => {
    if (!name1 || !name2) return
    setSubmitting(true)
    const [s1, s2] = await Promise.all([findPlayerByName(name1), findPlayerByName(name2)])
    setSubmitting(false)
    if (!s1 || !s2) {
      alert(`Не знайдено: ${!s1 ? name1 + ' ' : ''}${!s2 ? name2 : ''}`)
      return
    }
    navigate(`/compare/${encodeURIComponent(s1)}/${encodeURIComponent(s2)}`)
  }

  // Search form view
  if (!id1 || !id2) {
    return (
      <div className="max-w-2xl mx-auto p-6">
        <header className="mb-6">
          <h1 className="text-3xl font-bold mb-1">Порівняння гравців</h1>
          <p className="text-zinc-400 text-sm">
            Введи імена двох гравців для порівняння side-by-side
          </p>
        </header>
        <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-6 space-y-4">
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
            {submitting ? 'Шукаю…' : 'Порівняти'}
          </button>
        </div>
      </div>
    )
  }

  if (loading) return <div className="text-zinc-400 p-6 text-center">Завантаження…</div>
  if (error || !d1 || !d2) return <div className="text-red-400 p-6">{error ?? 'не вдалось завантажити'}</div>

  const p1 = d1.profile, p2 = d2.profile

  return (
    <div className="max-w-5xl mx-auto p-6">
      <Link to="/compare" className="text-zinc-400 hover:text-amber-400 text-sm">← Інше порівняння</Link>

      <header className="my-6">
        <h1 className="text-3xl font-bold text-center">Порівняння гравців</h1>
      </header>

      <div className="grid grid-cols-2 gap-8 mb-6">
        <PlayerHeader p={p1} />
        <PlayerHeader p={p2} />
      </div>

      {/* Head-to-head card — direct PvP kills derived from log_lines */}
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

      {/* Aggregate stats — colour shows who wins each row */}
      <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg overflow-hidden mb-6">
        <table className="w-full text-sm">
          <tbody>
            <StatRow label="Level"           valA={p1.level}             valB={p2.level} />
            <StatRow label="Kills"           valA={p1.kills}             valB={p2.kills} />
            <StatRow label="Deaths"          valA={p1.deaths}            valB={p2.deaths} higherBetter={false} />
            <StatRow label="K/D"             valA={p1.kd_ratio ?? 0}     valB={p2.kd_ratio ?? 0} />
            <StatRow label="KPM"             valA={p1.kpm ?? 0}          valB={p2.kpm ?? 0} />
            <StatRow label="Матчів"          valA={p1.matches_played}    valB={p2.matches_played} />
            <StatRow label="Годин"           valA={Math.floor(p1.total_seconds / 3600)} valB={Math.floor(p2.total_seconds / 3600)} />
            <StatRow label="Combat"          valA={p1.combat}            valB={p2.combat} />
            <StatRow label="Offense"         valA={p1.offense}           valB={p2.offense} />
            <StatRow label="Defense"         valA={p1.defense}           valB={p2.defense} />
            <StatRow label="Support"         valA={p1.support}           valB={p2.support} />
            <StatRow label="Best streak"     valA={p1.best_kills_streak} valB={p2.best_kills_streak} />
            <StatRow label="Найдовше життя (с)" valA={p1.longest_life_secs} valB={p2.longest_life_secs} />
            <StatRow label="Team kills"      valA={p1.teamkills}         valB={p2.teamkills} higherBetter={false} />
            <StatRow label="Смертей від ТК"  valA={p1.deaths_by_tk}      valB={p2.deaths_by_tk} higherBetter={false} />
          </tbody>
        </table>
      </div>

      {/* Top weapons — top 3 each side */}
      <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4 mb-6">
        <h2 className="text-zinc-300 uppercase text-xs tracking-widest mb-3 text-center">🔫 Топ-3 зброя</h2>
        <div className="grid grid-cols-2 gap-6">
          <ol className="space-y-1 text-sm">
            {d1.top_weapons.slice(0, 3).map((w, i) => (
              <li key={w.weapon} className="flex items-baseline gap-2">
                <span className="text-zinc-500 w-5 text-right">{i + 1}.</span>
                <span className="flex-1 truncate" title={w.weapon}>{w.weapon}</span>
                <span className="text-zinc-200 tabular-nums font-medium">{w.kills.toLocaleString('uk-UA')}</span>
              </li>
            ))}
            {d1.top_weapons.length === 0 && <li className="text-zinc-600 text-xs italic">немає даних</li>}
          </ol>
          <ol className="space-y-1 text-sm">
            {d2.top_weapons.slice(0, 3).map((w, i) => (
              <li key={w.weapon} className="flex items-baseline gap-2">
                <span className="text-zinc-500 w-5 text-right">{i + 1}.</span>
                <span className="flex-1 truncate" title={w.weapon}>{w.weapon}</span>
                <span className="text-zinc-200 tabular-nums font-medium">{w.kills.toLocaleString('uk-UA')}</span>
              </li>
            ))}
            {d2.top_weapons.length === 0 && <li className="text-zinc-600 text-xs italic">немає даних</li>}
          </ol>
        </div>
      </div>

      {/* Achievements — actual badges, not just counts */}
      <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4">
        <h2 className="text-zinc-300 uppercase text-xs tracking-widest mb-3 text-center">
          🏅 Досягнення ({d1.achievements.length} vs {d2.achievements.length})
        </h2>
        <div className="grid grid-cols-2 gap-6">
          <div className="flex flex-wrap gap-1.5">
            {d1.achievements.map((a) => <AchievementBadge key={a.id} a={a} />)}
            {d1.achievements.length === 0 && <div className="text-zinc-600 text-xs italic">немає досягнень</div>}
          </div>
          <div className="flex flex-wrap gap-1.5">
            {d2.achievements.map((a) => <AchievementBadge key={a.id} a={a} />)}
            {d2.achievements.length === 0 && <div className="text-zinc-600 text-xs italic">немає досягнень</div>}
          </div>
        </div>
      </div>
    </div>
  )
}
