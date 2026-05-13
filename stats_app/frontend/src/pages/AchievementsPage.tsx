import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { fetchAchievementStats, AchievementStat } from '../api/client'

const TIER_STYLES: Record<AchievementStat['tier'], string> = {
  common:    'bg-zinc-700/80 border-zinc-500/50 text-zinc-100',
  uncommon:  'bg-emerald-800/80 border-emerald-500/50 text-emerald-100',
  rare:      'bg-sky-800/80 border-sky-500/50 text-sky-100',
  epic:      'bg-violet-800/80 border-violet-500/50 text-violet-100',
  legendary: 'bg-amber-700/80 border-amber-500/60 text-amber-50',
  mythic:    'bg-gradient-to-r from-rose-900 to-violet-900 border-fuchsia-500/60 text-white',
}

function rarityBucket(pct: number): 'mythic' | 'legendary' | 'rare' | 'uncommon' | 'common' {
  if (pct < 0.1) return 'mythic'
  if (pct < 1) return 'legendary'
  if (pct < 5) return 'rare'
  if (pct < 20) return 'uncommon'
  return 'common'
}

export default function AchievementsPage() {
  const { t, i18n } = useTranslation()
  const nf = new Intl.NumberFormat(i18n.resolvedLanguage || i18n.language || 'en')
  const [items, setItems] = useState<AchievementStat[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchAchievementStats()
      .then(setItems)
      .finally(() => setLoading(false))
  }, [])

  const total = items[0]?.total_players ?? 0

  // Sort: rarest first (lowest percentage = most prestigious)
  const sortedItems = [...items].sort((a, b) => a.percentage - b.percentage)

  return (
    <div className="max-w-6xl mx-auto p-6">
      <header className="mb-6">
        <h1 className="text-3xl font-bold mb-1">{t('achievements.title')}</h1>
        <p className="text-zinc-400 text-sm">
          {t('achievements.subtitle', { count: items.length, total: nf.format(total) })}
        </p>
      </header>

      {loading && <div className="text-zinc-400 py-8 text-center">{t('common.loading')}</div>}

      {!loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {sortedItems.map((a) => (
            <Link
              key={a.id}
              to={`/achievements/${a.id}`}
              className={`block border rounded-lg p-4 hover:scale-[1.02] transition-transform ${TIER_STYLES[a.tier]}`}
            >
              <div className="flex items-baseline gap-2 mb-1">
                <span className="text-2xl">{a.icon}</span>
                {/* Achievement title + description stay Ukrainian by editorial
                    decision (Tier 2 in I18N_PLAN.md). The chrome around
                    them translates. */}
                <h3 className="font-semibold flex-1">{a.title}</h3>
                <span className="text-xs opacity-70 uppercase">{a.tier}</span>
              </div>
              <p className="text-xs opacity-80 mb-2 leading-snug">{a.description}</p>
              <div className="flex items-baseline justify-between text-sm">
                <span className="opacity-80">
                  {t('achievements.earnedBy', { count: nf.format(a.earned_count) })}
                </span>
                <span className="font-bold tabular-nums">{a.percentage}%</span>
              </div>
              <div className="mt-2 bg-black/30 h-1.5 rounded overflow-hidden">
                <div className="bg-white/70 h-full" style={{ width: `${Math.min(100, a.percentage)}%` }} />
              </div>
              <div className="mt-2 text-xs opacity-60 italic">
                {t('achievements.rarity', { tier: t(`achievements.tiers.${rarityBucket(a.percentage)}`) })}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
