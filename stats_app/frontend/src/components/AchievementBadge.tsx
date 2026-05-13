import { Link } from 'react-router-dom'
import { Achievement } from '../api/client'
import { useMetaLabel } from '../i18n/metaLabel'

const TIER_STYLES: Record<Achievement['tier'], string> = {
  common:    'bg-zinc-700/80 border-zinc-500/50 text-zinc-100',
  uncommon:  'bg-emerald-800/80 border-emerald-500/50 text-emerald-100',
  rare:      'bg-sky-800/80 border-sky-500/50 text-sky-100',
  epic:      'bg-violet-800/80 border-violet-500/50 text-violet-100',
  legendary: 'bg-amber-700/80 border-amber-500/60 text-amber-50',
  mythic:    'bg-gradient-to-r from-rose-900 to-violet-900 border-fuchsia-500/60 text-white',
}

interface Props {
  a: Achievement
  linkable?: boolean  // when true (default), wraps in Link to /achievements/:id
}

export default function AchievementBadge({ a, linkable = true }: Props) {
  const meta = useMetaLabel()
  // Translated when available; otherwise falls back to the Ukrainian text
  // the backend sent. See stats_app/I18N_PLAN.md (Tier 2).
  const title = meta.title('achievements', a.id, a.title)
  const desc = meta.description('achievements', a.id, a.description)
  const tooltip = desc ? `${title} (${a.tier})\n${desc}` : `${title} • ${a.tier}`
  const cls = `inline-flex items-center gap-1.5 px-2.5 py-1 rounded border text-xs font-medium ${TIER_STYLES[a.tier]}`
  const body = (
    <>
      <span className="text-base leading-none">{a.icon}</span>
      <span>{title}</span>
    </>
  )
  if (!linkable) {
    return <span className={cls} title={tooltip}>{body}</span>
  }
  return (
    <Link to={`/achievements/${a.id}`} className={`${cls} hover:scale-105 transition-transform`} title={tooltip}>
      {body}
    </Link>
  )
}
