/**
 * Persistent compare-list backed by localStorage.
 *
 * Up to 4 players can be queued; the floating <CompareBar> reads this list
 * and the "Порівняти (N)" button navigates to /compare/sid1,sid2,...
 * Storage key is namespaced so it doesn't collide with other localStorage data.
 *
 * Cross-tab sync: dispatches both a custom event ('compareList:change') for
 * same-tab updates and listens to the native 'storage' event for other tabs.
 */
import { useEffect, useState } from 'react'

const KEY = 'stats_app:compareList'
const MAX_ENTRIES = 4

export interface ComparePlayer {
  steam_id: string
  name: string
  added_at: string
}

function readList(): ComparePlayer[] {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.filter(
      (p) => p && typeof p.steam_id === 'string' && typeof p.name === 'string'
    ) as ComparePlayer[]
  } catch {
    return []
  }
}

function writeList(next: ComparePlayer[]) {
  try {
    localStorage.setItem(KEY, JSON.stringify(next))
  } catch {
    // quota or disabled — silently ignore; the UI still works in-memory
  }
  window.dispatchEvent(new Event('compareList:change'))
}

export function useCompareList() {
  const [list, setList] = useState<ComparePlayer[]>(() => readList())

  useEffect(() => {
    const onChange = () => setList(readList())
    window.addEventListener('compareList:change', onChange)
    window.addEventListener('storage', onChange)
    return () => {
      window.removeEventListener('compareList:change', onChange)
      window.removeEventListener('storage', onChange)
    }
  }, [])

  const add = (p: { steam_id: string; name: string }): 'added' | 'duplicate' | 'full' => {
    const current = readList()
    if (current.some((x) => x.steam_id === p.steam_id)) return 'duplicate'
    if (current.length >= MAX_ENTRIES) return 'full'
    writeList([...current, { ...p, added_at: new Date().toISOString() }])
    return 'added'
  }

  const remove = (steam_id: string) => {
    writeList(readList().filter((x) => x.steam_id !== steam_id))
  }

  const clear = () => writeList([])

  const has = (steam_id: string) => list.some((x) => x.steam_id === steam_id)

  return { list, add, remove, clear, has, max: MAX_ENTRIES }
}
