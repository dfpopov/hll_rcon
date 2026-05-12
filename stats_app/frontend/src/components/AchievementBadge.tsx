import { Link } from 'react-router-dom'
import { Achievement } from '../api/client'

const TIER_STYLES: Record<Achievement['tier'], string> = {
  common:    'bg-zinc-700/80 border-zinc-500/50 text-zinc-100',
  uncommon:  'bg-emerald-800/80 border-emerald-500/50 text-emerald-100',
  rare:      'bg-sky-800/80 border-sky-500/50 text-sky-100',
  epic:      'bg-violet-800/80 border-violet-500/50 text-violet-100',
  legendary: 'bg-amber-700/80 border-amber-500/60 text-amber-50',
  mythic:    'bg-gradient-to-r from-rose-900 to-violet-900 border-fuchsia-500/60 text-white',
}

// Predicate descriptions (Ukrainian) shown in tooltip — mirrors achievements.py
const ACH_DESCRIPTIONS: Record<string, string> = {
  centurion:     'Зіграти 100+ матчів',
  veteran:       'Зіграти 500+ матчів',
  lifetime:      'Зіграти 1000+ матчів',
  sharpshooter:  'Мати K/D 2.0+',
  elite_sniper:  'Мати K/D 3.0+',
  centurion_k:   'Зробити 100+ вбивств',
  killer_1k:     'Зробити 1000+ вбивств',
  killing_mach:  'Зробити 5000+ вбивств',
  reaper:        'Зробити 10000+ вбивств',
  unstoppable:   'Серія 30+ вбивств в одному матчі',
  legendary_st:  'Серія 60+ вбивств в одному матчі',
  god_mode:      'Серія 88+ вбивств в одному матчі',
  marathon:      '100+ годин у грі',
  time_lord:     '500+ годин у грі',
  combat_master: '100K+ combat score',
  support_hero:  '300K+ support score',
  defender:      '200K+ defense score',
  attacker:      '100K+ offense score',
  elite:         'Рівень 200+',
  legendary_lvl: 'Рівень 250+',
  mythic_lvl:    'Рівень 300+',
  survivor:      'Найдовше життя 10+ хвилин',
  tk_offender:   '100+ TK (team kills)',
  clumsy:        '100+ смертей від ТК своїх',
}

interface Props {
  a: Achievement
  linkable?: boolean  // when true (default), wraps in Link to /achievements/:id
}

export default function AchievementBadge({ a, linkable = true }: Props) {
  const desc = ACH_DESCRIPTIONS[a.id] ?? ''
  const tooltip = desc ? `${a.title} (${a.tier})\n${desc}` : `${a.title} • ${a.tier}`
  const cls = `inline-flex items-center gap-1.5 px-2.5 py-1 rounded border text-xs font-medium ${TIER_STYLES[a.tier]}`
  const body = (
    <>
      <span className="text-base leading-none">{a.icon}</span>
      <span>{a.title}</span>
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
