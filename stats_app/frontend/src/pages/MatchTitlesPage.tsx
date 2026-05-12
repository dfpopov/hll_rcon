/**
 * Reference page listing every match title that can appear next to a
 * recent-matches entry, along with its trigger condition. The source of
 * truth is MATCH_TITLES exported from PlayerMemes.
 */
import { MATCH_TITLES } from '../components/PlayerMemes'

// Loose visual buckets — just for grouping headings, not enforced.
const CATEGORIES: { label: string; ids: string[]; emoji: string }[] = [
  { label: 'Катастрофи', emoji: '💀', ids: ['spectator', 'safari', 'sacrificial_m', 'dark_hour', 'bloodbath'] },
  { label: 'Бог-tier ratios', emoji: '👑', ids: ['sniper_ghost', 'perfect', 'eagle_eye'] },
  { label: 'Об\'єм', emoji: '🔥', ids: ['terror', 'massacre', 'god_of_war', 'untouchable', 'cold_blooded', 'duelist'] },
  { label: 'Support / Defense', emoji: '🛡', ids: ['invisible_helper', 'quiet_victory', 'wall_m'] },
  { label: 'Меми', emoji: '🎲', ids: ['mirror', 'zen'] },
]

export default function MatchTitlesPage() {
  return (
    <div className="max-w-5xl mx-auto p-6">
      <header className="mb-6">
        <h1 className="text-3xl font-bold mb-1">🏷 Титули матчів</h1>
        <p className="text-zinc-400 text-sm">
          {MATCH_TITLES.length} варіантів — присуджується автоматично в таблиці «Останні матчі» якщо матч підпадає під одну з умов нижче. Перевіряється у порядку: катастрофи → бог-tier → об\'єм → support → меми.
        </p>
      </header>

      <div className="space-y-6">
        {CATEGORIES.map((cat) => {
          const items = cat.ids
            .map((id) => MATCH_TITLES.find((t) => t.id === id))
            .filter(Boolean) as typeof MATCH_TITLES
          return (
            <section key={cat.label}>
              <h2 className="text-zinc-300 uppercase text-xs tracking-widest mb-3">
                {cat.emoji} {cat.label}
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {items.map((t) => (
                  <div key={t.id} className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-3">
                    <div className="flex items-baseline gap-2 mb-1">
                      <span className="text-2xl leading-none">{t.emoji}</span>
                      <h3 className="font-semibold text-amber-200">{t.title}</h3>
                    </div>
                    <p className="text-xs text-zinc-400 leading-snug">{t.description}</p>
                  </div>
                ))}
              </div>
            </section>
          )
        })}
      </div>
    </div>
  )
}
