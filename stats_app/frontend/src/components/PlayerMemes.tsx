/**
 * Memey / personality highlight cards derived purely from the existing
 * PlayerDetail payload — no new endpoints. Three blocks:
 *   - NemesisStamp: top-1 killed_by entry as the player's eternal rival.
 *   - LovedHatedMap: from top_maps sort by K/D (loved = highest, hated = lowest).
 *   - PlaystyleTag: bucket the player into a roleplay archetype based on
 *     combat/offense/defense/support distribution + K/D and streak.
 */
import { PlayerDetail, PlayerTopMap, PlayerProfile } from '../api/client'

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
      <div className="text-lg font-bold mt-1 break-all">{map.map_name}</div>
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

// ── Playstyle classifier ──────────────────────────────────────────────────

interface Playstyle {
  emoji: string
  title: string
  description: string
  color: string
}

export function classifyPlaystyle(p: PlayerProfile): Playstyle {
  const total = (p.combat ?? 0) + (p.offense ?? 0) + (p.defense ?? 0) + (p.support ?? 0)
  if (total === 0) return {
    emoji: '🛡', title: 'Універсал', color: 'text-zinc-300',
    description: 'Замало даних для висновку.',
  }
  const cp = (p.combat  ?? 0) / total * 100
  const op = (p.offense ?? 0) / total * 100
  const dp = (p.defense ?? 0) / total * 100
  const sp = (p.support ?? 0) / total * 100
  const kd = p.kd_ratio ?? 0
  const streak = p.best_kills_streak ?? 0
  const kpm = p.kpm ?? 0

  if (sp >= 50) return {
    emoji: '📦', title: 'Логіст',
    color: 'text-cyan-300',
    description: `${sp.toFixed(0)}% support — будуєш, постачаєш, рятуєш. Грудьми не закриваєш — але без тебе не виграти.`,
  }
  if (kd >= 2.5 && streak >= 30) return {
    emoji: '🎯', title: 'Снайпер-вбивця',
    color: 'text-amber-300',
    description: `K/D ${kd.toFixed(2)}, серія ${streak}. Дивишся в приціл, інші дивляться в землю.`,
  }
  if (kpm >= 1.5 && cp >= 40) return {
    emoji: '🔥', title: 'Молотобоєць',
    color: 'text-orange-300',
    description: `${kpm.toFixed(2)} вбивств/хв при ${cp.toFixed(0)}% combat. Рук не опускаєш, ноги не зупиняються.`,
  }
  if (cp >= 50) {
    if (dp > op) return {
      emoji: '🏰', title: 'Захисник окопу',
      color: 'text-emerald-300',
      description: `${cp.toFixed(0)}% combat + ${dp.toFixed(0)}% defense. Сидиш на точці, переробляєш ворогів на фарш.`,
    }
    return {
      emoji: '⚔️', title: 'Бойовий жнець',
      color: 'text-red-300',
      description: `${cp.toFixed(0)}% combat. Усе про вбивства, мало про задачі.`,
    }
  }
  if (op > dp + 15) return {
    emoji: '🗡', title: 'Штурмовик',
    color: 'text-orange-300',
    description: `${op.toFixed(0)}% offense. Завжди першим на точці. Помираєш швидко, але корисно.`,
  }
  if (dp > op + 15) return {
    emoji: '🛡', title: 'Стіна',
    color: 'text-blue-300',
    description: `${dp.toFixed(0)}% defense. Точка не падає, поки ти живий.`,
  }
  // K/D extremes for balanced players
  if (kd >= 2.0) return {
    emoji: '🦅', title: 'Влучний універсал',
    color: 'text-amber-300',
    description: `K/D ${kd.toFixed(2)}, збалансовані бали. Робиш все потроху, але точно.`,
  }
  if (kd < 0.8) return {
    emoji: '💀', title: 'Жертовний',
    color: 'text-rose-300',
    description: `K/D ${kd.toFixed(2)}. Кидаєшся в саме пекло — хтось має бути першим.`,
  }
  return {
    emoji: '🛡', title: 'Універсал',
    color: 'text-zinc-300',
    description: 'Стиль збалансований: трохи бою, трохи цілей, трохи допомоги.',
  }
}

export function PlaystyleCard({ p }: { p: PlayerProfile }) {
  const style = classifyPlaystyle(p)
  return (
    <section className="mb-6 bg-zinc-900/60 border border-zinc-800 rounded-lg p-4">
      <div className="flex items-center gap-4">
        <div className="text-5xl">{style.emoji}</div>
        <div className="flex-1">
          <div className="text-xs text-zinc-500 uppercase tracking-widest">Стиль гри</div>
          <div className={`text-xl font-bold ${style.color}`}>{style.title}</div>
          <p className="text-sm text-zinc-400 mt-1">{style.description}</p>
        </div>
      </div>
    </section>
  )
}
