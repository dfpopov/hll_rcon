/**
 * Memey / personality highlight cards derived purely from the existing
 * PlayerDetail payload — no new endpoints. Three blocks:
 *   - NemesisStamp: top-1 killed_by entry as the player's eternal rival.
 *   - LovedHatedMap: from top_maps sort by K/D (loved = highest, hated = lowest).
 *   - PlaystyleTag: bucket the player into a roleplay archetype based on
 *     combat/offense/defense/support distribution + K/D and streak.
 */
import { PlayerDetail, PlayerTopMap, Playstyle } from '../api/client'
import { formatMapName } from './mapNames'

// ── Nemesis ────────────────────────────────────────────────────────────────

export function NemesisStamp({ d }: { d: PlayerDetail }) {
  const top = d.killed_by?.[0]
  if (!top || top.deaths == null || top.deaths < 5) return null  // hide for noise
  return (
    <section className="mb-6 bg-gradient-to-r from-rose-900/40 via-zinc-900 to-zinc-900 border border-rose-700/50 rounded-lg p-4">
      <div className="flex items-center gap-4">
        <div className="text-5xl">😡</div>
        <div className="flex-1">
          <div className="text-xs text-rose-300 uppercase tracking-widest">Твій вічний ворог</div>
          <div className="text-2xl font-bold text-rose-100">{top.killer}</div>
          <div className="text-sm text-zinc-300 mt-1">
            убив тебе <span className="font-bold text-rose-300 tabular-nums">{top.deaths}</span> разів —
            {top.deaths >= 50 ? ' просто ганьба.' :
             top.deaths >= 20 ? ' пора відомстити.' :
             ' тримай очі відкритими.'}
          </div>
        </div>
      </div>
    </section>
  )
}

// ── Loved / Hated map ─────────────────────────────────────────────────────

function MapCard({ map, tone, label, emoji }: { map: PlayerTopMap; tone: 'good' | 'bad'; label: string; emoji: string }) {
  const color = tone === 'good' ? 'text-emerald-300 border-emerald-700/40' : 'text-rose-300 border-rose-700/40'
  return (
    <div className={`bg-zinc-900/60 border rounded-lg p-4 ${color.split(' ')[1]}`}>
      <div className={`text-xs uppercase tracking-widest ${color.split(' ')[0]}`}>{emoji} {label}</div>
      <div className="text-lg font-bold mt-1 break-all" title={map.map_name}>{formatMapName(map.map_name)}</div>
      <div className="text-sm text-zinc-400 mt-1">
        K/D <span className={`font-bold tabular-nums ${color.split(' ')[0]}`}>{map.kd ?? '—'}</span>
        {' • '}{map.matches} матчів • {map.kills?.toLocaleString('uk-UA') ?? 0} вбивств
      </div>
    </div>
  )
}

export function LovedHatedMap({ topMaps }: { topMaps: PlayerTopMap[] }) {
  // Need at least 3 matches per map for the K/D to mean something.
  const meaningful = topMaps.filter((m) => (m.matches ?? 0) >= 3 && m.kd != null)
  if (meaningful.length < 2) return null
  const sorted = [...meaningful].sort((a, b) => (b.kd ?? 0) - (a.kd ?? 0))
  const loved = sorted[0]
  const hated = sorted[sorted.length - 1]
  if (loved.map_name === hated.map_name) return null
  return (
    <section className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-6">
      <MapCard map={loved} tone="good" label="Улюблена карта" emoji="💚" />
      <MapCard map={hated} tone="bad"  label="Прокляте місце" emoji="💀" />
    </section>
  )
}

// Playstyle classifier was moved to backend (playstyles.py) as a single
// source of truth — used by player_detail and /api/playstyles. The
// PlaystyleCard component below renders the API-supplied object.

// ── Match titles ──────────────────────────────────────────────────────────

export interface MatchTitle {
  id: string
  emoji: string
  title: string
  description: string
}

/** Full catalogue of match titles. Order matters in matchTitle below —
 *  most specific / most disastrous first. This list is also used by the
 *  /match-titles reference page. */
export const MATCH_TITLES: (MatchTitle & {
  predicate: (m: MatchTitleInput) => boolean
})[] = [
  // ── Disaster cases ─────────────────────────────────────────────────
  { id: 'spectator', emoji: '🛌', title: 'Глядач',
    description: '0 kills 0 deaths при перебуванні в матчі 5+ хв',
    predicate: (m) => m.kills === 0 && m.deaths === 0 && (m.time_seconds ?? 0) >= 300 },
  { id: 'safari', emoji: '☠', title: 'Сафарі для ворога',
    description: '50+ смертей при менше ніж 10 вбивствах',
    predicate: (m) => m.deaths >= 50 && m.kills < 10 },
  { id: 'sacrificial_m', emoji: '💀', title: 'Жертовний',
    description: '20+ смертей без жодного вбивства',
    predicate: (m) => m.kills === 0 && m.deaths >= 20 },
  { id: 'dark_hour', emoji: '🪦', title: 'Чорна година',
    description: '5 або менше вбивств при 30+ смертях',
    predicate: (m) => m.kills <= 5 && m.deaths >= 30 },
  { id: 'bloodbath', emoji: '🩸', title: 'Бійня для тебе',
    description: '40+ смертей у матчі',
    predicate: (m) => m.deaths >= 40 },

  // ── God-tier ratios (priority over high-volume) ────────────────────
  { id: 'sniper_ghost', emoji: '🐍', title: 'Снайпер духу',
    description: 'K/D 10+ при 10+ вбивствах — нереально точно',
    predicate: (m) => (m.kd ?? 0) >= 10 && m.kills >= 10 },
  { id: 'perfect', emoji: '🥇', title: 'Ідеальний',
    description: '20+ вбивств і жодної смерті — повне домінування',
    predicate: (m) => m.kills >= 20 && m.deaths === 0 },
  { id: 'eagle_eye', emoji: '🦅', title: 'Орлине око',
    description: 'K/D 7+ при 15+ вбивствах',
    predicate: (m) => (m.kd ?? 0) >= 7 && m.kills >= 15 },

  // ── High volume both ways (must come BEFORE narrower kills-only) ──
  { id: 'training', emoji: '🚂', title: 'Тренування',
    description: '50+ вбивств І 50+ смертей — інтенсивна нічия',
    predicate: (m) => m.kills >= 50 && m.deaths >= 50 },
  { id: 'frenzy', emoji: '💢', title: 'Скажений',
    description: '50+ вбивств і 30+ смертей — об\'єм в обидві сторони',
    predicate: (m) => m.kills >= 50 && m.deaths >= 30 },

  // ── High volume ────────────────────────────────────────────────────
  { id: 'terror', emoji: '👹', title: 'Терор',
    description: '100+ вбивств за один матч',
    predicate: (m) => m.kills >= 100 },
  { id: 'massacre', emoji: '🔥', title: 'Різанина',
    description: '80+ вбивств за один матч',
    predicate: (m) => m.kills >= 80 },
  { id: 'merciless', emoji: '🦅', title: 'Безжальний',
    description: '40+ вбивств при K/D 3+',
    predicate: (m) => m.kills >= 40 && (m.kd ?? 0) >= 3 },
  { id: 'speedrun', emoji: '🏃', title: 'Спідран',
    description: '30+ вбивств за матч до 30 хвилин',
    predicate: (m) => m.kills >= 30 && (m.time_seconds ?? 99999) < 1800 },
  { id: 'machine_gunner', emoji: '🪖', title: 'Кулеметник',
    description: 'Combat 1500+ при 30+ kills і не більш ніж 10 смертях',
    predicate: (m) => m.combat >= 1500 && m.kills >= 30 && m.deaths <= 10 },
  { id: 'god_of_war', emoji: '⚡', title: 'Бог війни',
    description: '50+ вбивств при K/D 3+',
    predicate: (m) => m.kills >= 50 && (m.kd ?? 0) >= 3 },
  { id: 'untouchable', emoji: '🎯', title: 'Невловимий',
    description: '30+ вбивств при K/D 5+',
    predicate: (m) => m.kills >= 30 && (m.kd ?? 0) >= 5 },
  { id: 'cold_blooded', emoji: '👑', title: 'Холоднокровний',
    description: 'K/D 5+ при 20+ вбивствах',
    predicate: (m) => (m.kd ?? 0) >= 5 && m.kills >= 20 },
  { id: 'duelist', emoji: '🥊', title: 'Дуелянт',
    description: 'Близька гра — 15+ вбивств, 15+ смертей, різниця ≤ 2',
    predicate: (m) => m.kills >= 15 && m.deaths >= 15 && Math.abs(m.kills - m.deaths) <= 2 },

  // ── Support / defense heroes ───────────────────────────────────────
  { id: 'invisible_helper', emoji: '📦', title: 'Невидимий помічник',
    description: 'Support 8000+ при менш ніж 5 вбивствах — пасивний герой',
    predicate: (m) => m.support > 8000 && m.kills < 5 },
  { id: 'quiet_victory', emoji: '📦', title: 'Тиха перемога',
    description: 'Support 5000+ при менш ніж 10 вбивствах',
    predicate: (m) => m.support > 5000 && m.kills < 10 },
  { id: 'wall_m', emoji: '🏯', title: 'Стіна',
    description: 'Combat 3000+ при не більш ніж 3 смертях — точка тримається',
    predicate: (m) => m.combat > 3000 && m.deaths <= 3 },

  // ── Edge case memes ────────────────────────────────────────────────
  { id: 'mirror', emoji: '⚖', title: 'Дзеркало',
    description: 'K точно дорівнює D при 30+ вбивствах',
    predicate: (m) => m.kills === m.deaths && m.kills >= 30 },
  { id: 'zen', emoji: '🎲', title: 'Дзен',
    description: 'K точно дорівнює D при 10-29 вбивствах',
    predicate: (m) => m.kills === m.deaths && m.kills >= 10 && m.kills < 30 },
]

export interface MatchTitleInput {
  kills: number; deaths: number; kd: number | null
  combat: number; support: number; map_name: string
  time_seconds?: number
}

/** Auto-generated meme-y title for an outstanding match. Returns null when
 *  the match is unremarkable. */
export function matchTitle(m: MatchTitleInput): MatchTitle | null {
  for (const t of MATCH_TITLES) {
    try {
      if (t.predicate(m)) return { id: t.id, emoji: t.emoji, title: t.title, description: t.description }
    } catch { /* skip on bad input */ }
  }
  return null
}

import { Link } from 'react-router-dom'

/** Renders the API-supplied primary playstyle + a chip row of other
 *  matching archetypes (also). Primary card links to /playstyles/{id};
 *  each chip links to its own /playstyles/{id} page too. */
export function PlaystyleCard({ playstyle, also = [] }: { playstyle: Playstyle; also?: Playstyle[] }) {
  return (
    <section className="mb-6 bg-zinc-900/60 border border-zinc-800 rounded-lg p-4">
      <Link to={`/playstyles/${playstyle.id}`}
        className="flex items-center gap-4 hover:bg-zinc-900 -m-1 p-1 rounded transition-colors">
        <div className="text-5xl">{playstyle.emoji}</div>
        <div className="flex-1">
          <div className="text-xs text-zinc-500 uppercase tracking-widest">Стиль гри · основний</div>
          <div className={`text-xl font-bold ${playstyle.color}`}>{playstyle.title}</div>
          <p className="text-sm text-zinc-400 mt-1">{playstyle.description}</p>
        </div>
      </Link>
      {also.length > 0 && (
        <div className="mt-3 pt-3 border-t border-zinc-800">
          <div className="text-[10px] uppercase text-zinc-600 tracking-widest mb-2">Також підходить</div>
          <div className="flex flex-wrap gap-1.5">
            {also.map((ps) => (
              <Link key={ps.id} to={`/playstyles/${ps.id}`}
                className={`text-xs px-2 py-1 rounded bg-zinc-800/60 border border-zinc-800
                            hover:bg-zinc-800 hover:border-zinc-700 ${ps.color}`}
                title={ps.description}>
                {ps.emoji} {ps.title}
              </Link>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}
