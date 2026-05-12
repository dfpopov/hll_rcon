/**
 * Tiny ⚖ icon button to add/remove a player to the localStorage compare
 * list, designed to sit inline next to any Link to /player/:steam_id.
 *
 * States:
 *   - not in list, list has room: amber ⚖ on hover, click adds
 *   - already in list: filled green ✓ on hover, click removes
 *   - list at max (4): muted grey, disabled, with tooltip
 */
import { useCompareList } from '../hooks/useCompareList'

interface Props {
  steam_id: string
  name: string
  /** Override visual size — defaults to "sm" (compact 18px), use "md" for prominent placements. */
  size?: 'sm' | 'md'
}

export default function MiniCompareButton({ steam_id, name, size = 'sm' }: Props) {
  const { has, add, remove, list, max } = useCompareList()
  const inList = has(steam_id)
  const full = !inList && list.length >= max

  const onClick = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (inList) {
      remove(steam_id)
    } else if (!full) {
      add({ steam_id, name })
    }
  }

  const px = size === 'md' ? 'w-6 h-6 text-sm' : 'w-5 h-5 text-xs'
  const baseCls = `inline-flex items-center justify-center rounded ${px} shrink-0`
  if (inList) {
    return (
      <button onClick={onClick}
        className={`${baseCls} bg-amber-700/40 border border-amber-600/50 text-amber-200 hover:bg-amber-700/60`}
        title={`Прибрати ${name} зі списку порівняння`}>✓</button>
    )
  }
  if (full) {
    return (
      <button disabled
        className={`${baseCls} bg-zinc-800 border border-zinc-700 text-zinc-600 cursor-not-allowed`}
        title={`Список порівняння повний (${max}). Прибери когось щоб додати.`}>⚖</button>
    )
  }
  return (
    <button onClick={onClick}
      className={`${baseCls} bg-zinc-800 border border-transparent text-zinc-500 hover:text-amber-400 hover:border-amber-700/40`}
      title={`Додати ${name} до порівняння`}>⚖</button>
  )
}
