/**
 * Level rarity badge — colors INVERTED from typical UX so that high levels
 * look "rare / elite" (cold/dark colors), low levels look "common" (warm/neutral).
 *
 * Tier breaks (MMO-style rarity):
 *   0-49    common      gray
 *   50-99   uncommon    emerald (green)
 *   100-149 rare        sky (blue)
 *   150-199 epic        violet (purple)
 *   200-249 legendary   fuchsia (deep purple)
 *   250+    mythic      black with subtle purple ring (highest)
 */
interface LevelBadgeProps {
  level: number
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export function levelBadgeColor(level: number): string {
  if (level >= 250) return 'bg-gradient-to-br from-zinc-950 to-violet-950 ring-1 ring-fuchsia-500/50'
  if (level >= 200) return 'bg-gradient-to-br from-fuchsia-700 to-fuchsia-900'
  if (level >= 150) return 'bg-gradient-to-br from-violet-600 to-violet-800'
  if (level >= 100) return 'bg-gradient-to-br from-sky-500 to-sky-700'
  if (level >= 50)  return 'bg-gradient-to-br from-emerald-500 to-emerald-700'
  return 'bg-gradient-to-br from-zinc-500 to-zinc-700'
}

export default function LevelBadge({ level, size = 'sm', className = '' }: LevelBadgeProps) {
  const sizeClass = {
    sm: 'min-w-[2.5rem] px-1.5 py-0.5 text-xs',
    md: 'min-w-[3rem] px-3 py-2 text-lg',
    lg: 'min-w-[4rem] px-4 py-3 text-2xl',
  }[size]

  return (
    <span
      className={`inline-flex items-center justify-center rounded font-bold text-white ${levelBadgeColor(
        level,
      )} ${sizeClass} ${className}`}
      title={`Рівень ${level}`}
    >
      {level}
    </span>
  )
}
