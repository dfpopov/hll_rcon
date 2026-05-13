/**
 * Floating compare-bar at the bottom of the viewport.
 *
 * Hidden when no players are queued. Becomes visible when the user adds at
 * least one. Going to /compare needs >=2 players, so the CTA is disabled
 * for a single-player list.
 */
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useCompareList } from '../hooks/useCompareList'

export default function CompareBar() {
  const { t } = useTranslation()
  const { list, remove, clear, max } = useCompareList()
  const navigate = useNavigate()

  if (list.length === 0) return null

  const goCompare = () => {
    if (list.length < 2) return
    const ids = list.map((p) => encodeURIComponent(p.steam_id)).join(',')
    navigate(`/compare/${ids}`)
  }

  return (
    <div
      className="fixed bottom-4 left-1/2 -translate-x-1/2 z-40 bg-zinc-900/95 border border-zinc-700
                 rounded-lg shadow-2xl px-4 py-3 flex items-center gap-3 max-w-[95vw] backdrop-blur"
      role="region"
      aria-label={t('compareBar.regionLabel')}
    >
      <span className="text-xs text-zinc-400 uppercase tracking-widest hidden sm:inline">
        ⚖ {t('compareBar.label')}
      </span>
      <div className="flex items-center gap-1.5 flex-wrap">
        {list.map((p) => (
          <span
            key={p.steam_id}
            className="inline-flex items-center gap-1 px-2 py-1 rounded bg-zinc-800 text-sm border border-zinc-700"
          >
            <span className="max-w-[140px] truncate" title={p.name}>{p.name}</span>
            <button
              onClick={() => remove(p.steam_id)}
              className="text-zinc-500 hover:text-red-400 leading-none"
              title={t('compareBar.remove')}
              aria-label={t('compareBar.removeName', { name: p.name })}
            >✕</button>
          </span>
        ))}
        <span className="text-xs text-zinc-600 tabular-nums">{list.length}/{max}</span>
      </div>
      <button
        onClick={goCompare}
        disabled={list.length < 2}
        className="px-3 py-1.5 rounded bg-amber-600 hover:bg-amber-500 text-white text-sm font-medium
                   disabled:opacity-30 disabled:cursor-not-allowed"
        title={list.length < 2 ? t('compareBar.needTwo') : t('compareBar.go')}
      >
        {t('compareBar.compareN', { n: list.length })}
      </button>
      <button
        onClick={clear}
        className="text-xs text-zinc-500 hover:text-zinc-300"
        title={t('compareBar.clearAll')}
      >{t('compareBar.clear')}</button>
    </div>
  )
}
