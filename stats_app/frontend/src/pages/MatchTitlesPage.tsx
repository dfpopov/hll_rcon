/**
 * Reference page listing every match title that can appear next to a
 * recent-matches entry, along with its trigger condition. The source of
 * truth is MATCH_TITLES exported from PlayerMemes.
 */
import { useTranslation } from 'react-i18next'
import { MATCH_TITLES } from '../components/PlayerMemes'

// Loose visual buckets — labels translated via `matchTitles.categories.*`.
const CATEGORIES: { id: string; ids: string[]; emoji: string }[] = [
  { id: 'disasters',   emoji: '💀', ids: ['spectator', 'safari', 'sacrificial_m', 'dark_hour', 'bloodbath'] },
  { id: 'godRatios',   emoji: '👑', ids: ['sniper_ghost', 'perfect', 'eagle_eye'] },
  { id: 'volume',      emoji: '🔥', ids: ['terror', 'massacre', 'god_of_war', 'untouchable', 'cold_blooded', 'duelist'] },
  { id: 'support',     emoji: '🛡', ids: ['invisible_helper', 'quiet_victory', 'wall_m'] },
  { id: 'memes',       emoji: '🎲', ids: ['mirror', 'zen'] },
]

export default function MatchTitlesPage() {
  const { t } = useTranslation()
  return (
    <div className="max-w-5xl mx-auto p-6">
      <header className="mb-6">
        <h1 className="text-3xl font-bold mb-1">{t('matchTitles.title')}</h1>
        <p className="text-zinc-400 text-sm">
          {t('matchTitles.subtitle', { count: MATCH_TITLES.length })}
        </p>
      </header>

      <div className="space-y-6">
        {CATEGORIES.map((cat) => {
          const items = cat.ids
            .map((id) => MATCH_TITLES.find((mt) => mt.id === id))
            .filter(Boolean) as typeof MATCH_TITLES
          return (
            <section key={cat.id}>
              <h2 className="text-zinc-300 uppercase text-xs tracking-widest mb-3">
                {cat.emoji} {t(`matchTitles.categories.${cat.id}`)}
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {items.map((mt) => (
                  <div key={mt.id} className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-3">
                    <div className="flex items-baseline gap-2 mb-1">
                      <span className="text-2xl leading-none">{mt.emoji}</span>
                      {/* Match title names + descriptions stay Ukrainian per
                          Tier 4 editorial decision (I18N_PLAN.md). */}
                      <h3 className="font-semibold text-amber-200">{mt.title}</h3>
                    </div>
                    <p className="text-xs text-zinc-400 leading-snug">{mt.description}</p>
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
