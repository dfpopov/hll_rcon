/**
 * Global player search in the top nav. Standalone autocomplete — click
 * navigates straight to /player/:steam_id, doesn't touch any leaderboard
 * filter state. Reuses /api/players/autocomplete which matches across
 * historical names.
 */
import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { fetchAutocomplete, AutocompletePlayer } from '../api/client'
import Avatar from './Avatar'

export default function NavSearch() {
  const { t } = useTranslation()
  const [q, setQ] = useState('')
  const [suggestions, setSuggestions] = useState<AutocompletePlayer[]>([])
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

  useEffect(() => {
    const trimmed = q.trim()
    if (trimmed.length < 2) { setSuggestions([]); return }
    let cancelled = false
    const t = setTimeout(() => {
      fetchAutocomplete(trimmed, 8)
        .then((rs) => { if (!cancelled) setSuggestions(rs) })
        .catch(() => { if (!cancelled) setSuggestions([]) })
    }, 200)
    return () => { cancelled = true; clearTimeout(t) }
  }, [q])

  // Close on outside click / Esc.
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { setOpen(false) }
      // Enter navigates to first match if any
      if (e.key === 'Enter' && open && suggestions.length > 0
          && containerRef.current?.contains(document.activeElement)) {
        navigate(`/player/${suggestions[0].steam_id}`)
        setQ('')
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', onClick)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onClick)
      document.removeEventListener('keydown', onKey)
    }
  }, [open, suggestions, navigate])

  return (
    <div ref={containerRef} className="relative ml-auto">
      <div className="relative">
        <input
          type="text"
          value={q}
          onChange={(e) => { setQ(e.target.value); setOpen(true) }}
          onFocus={() => setOpen(true)}
          placeholder={t('nav.searchPlayer')}
          className="w-56 bg-zinc-800/80 text-zinc-100 px-3 py-1.5 rounded text-sm placeholder-zinc-500
                     focus:outline-none focus:ring-2 focus:ring-amber-500/50 focus:bg-zinc-800"
        />
        {q && (
          <button
            onClick={() => { setQ(''); setSuggestions([]); setOpen(false) }}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-200 text-xs"
            title={t('filters.clear')}
          >✕</button>
        )}
      </div>
      {open && suggestions.length > 0 && (
        <div className="absolute top-full right-0 mt-1 w-72 bg-zinc-900 border border-zinc-700 rounded-lg
                        shadow-2xl z-50 max-h-80 overflow-y-auto">
          {suggestions.map((s) => (
            <Link
              key={s.steam_id}
              to={`/player/${s.steam_id}`}
              onClick={() => { setOpen(false); setQ('') }}
              className="flex items-center gap-2 px-3 py-2 hover:bg-zinc-800 border-b border-zinc-800 last:border-0"
            >
              <Avatar url={s.avatar_url} name={s.name} size={24} />
              <span className="flex-1 text-sm text-zinc-200 truncate">{s.name}</span>
              <span className="text-xs text-zinc-500 tabular-nums">{s.matches}m</span>
            </Link>
          ))}
        </div>
      )}
      {open && q.trim().length >= 2 && suggestions.length === 0 && (
        <div className="absolute top-full right-0 mt-1 w-72 bg-zinc-900 border border-zinc-700 rounded-lg
                        shadow-2xl z-50 px-3 py-2 text-sm text-zinc-500 italic">
          нічого не знайдено
        </div>
      )}
    </div>
  )
}
