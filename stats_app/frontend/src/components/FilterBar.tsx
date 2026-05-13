import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  fetchMaps, fetchWeapons, fetchWeaponClasses, fetchAutocomplete,
  AutocompletePlayer, Period, GameMode, Side, WeaponClass,
} from '../api/client'
import Avatar from './Avatar'
import { formatMapName } from './mapNames'

interface FilterBarProps {
  search: string
  period: Period
  gameMode: GameMode
  minMatches: number
  weapon: string
  weaponClass: string
  mapName: string
  side: Side
  onChange: (next: {
    search?: string
    period?: Period
    gameMode?: GameMode
    minMatches?: number
    weapon?: string
    weaponClass?: string
    mapName?: string
    side?: Side
  }) => void
  onReset: () => void
}

export default function FilterBar({
  search, period, gameMode, minMatches, weapon, weaponClass, mapName, side,
  onChange, onReset,
}: FilterBarProps) {
  const { t } = useTranslation()
  const [maps, setMaps] = useState<string[]>([])
  const [weapons, setWeapons] = useState<string[]>([])
  const [classes, setClasses] = useState<WeaponClass[]>([])
  const [localSearch, setLocalSearch] = useState(search)

  // Autocomplete state — fires on every keystroke (debounced), independent
  // of the leaderboard filter commit. Clicking a suggestion jumps to the
  // player profile directly; clicking outside or pressing Esc closes.
  const [suggestions, setSuggestions] = useState<AutocompletePlayer[]>([])
  const [showDropdown, setShowDropdown] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchMaps().then(setMaps).catch(() => {})
    fetchWeapons().then(setWeapons).catch(() => {})
    fetchWeaponClasses().then(setClasses).catch(() => {})
  }, [])

  useEffect(() => { setLocalSearch(search) }, [search])

  useEffect(() => {
    if (localSearch === search) return
    const t = setTimeout(() => onChange({ search: localSearch }), 300)
    return () => clearTimeout(t)
  }, [localSearch])  // eslint-disable-line react-hooks/exhaustive-deps

  // Autocomplete: separate debounce on the unfiltered localSearch.
  useEffect(() => {
    const q = localSearch.trim()
    if (q.length < 2) { setSuggestions([]); return }
    let cancelled = false
    const t = setTimeout(() => {
      fetchAutocomplete(q, 8)
        .then((rs) => { if (!cancelled) setSuggestions(rs) })
        .catch(() => { if (!cancelled) setSuggestions([]) })
    }, 200)
    return () => { cancelled = true; clearTimeout(t) }
  }, [localSearch])

  // Close dropdown on outside click or Esc.
  useEffect(() => {
    const onClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setShowDropdown(false)
      }
    }
    const onEsc = (e: KeyboardEvent) => { if (e.key === 'Escape') setShowDropdown(false) }
    document.addEventListener('mousedown', onClickOutside)
    document.addEventListener('keydown', onEsc)
    return () => {
      document.removeEventListener('mousedown', onClickOutside)
      document.removeEventListener('keydown', onEsc)
    }
  }, [])

  const hasActive = period || gameMode || weapon || weaponClass || mapName || search || side || minMatches !== 30

  return (
    <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4 mb-4">
      <div className="flex flex-wrap gap-3 items-end">
        <div className="flex-grow min-w-[220px] max-w-md" ref={containerRef}>
          <label className="block text-xs text-zinc-400 mb-1">
            {t('filters.search')} <span className="text-zinc-600">{t('filters.searchHint')}</span>
          </label>
          <div className="relative">
            <input
              type="text"
              value={localSearch}
              onChange={(e) => { setLocalSearch(e.target.value); setShowDropdown(true) }}
              onFocus={() => setShowDropdown(true)}
              placeholder={t('filters.searchPlaceholder')}
              className="w-full bg-zinc-800 text-zinc-100 px-3 py-2 pr-8 rounded text-sm placeholder-zinc-500
                         focus:outline-none focus:ring-2 focus:ring-amber-500/50"
            />
            {localSearch && (
              <button
                onClick={() => { setLocalSearch(''); setSuggestions([]); setShowDropdown(false) }}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-200"
                title={t('filters.clear')}
              >✕</button>
            )}
            {showDropdown && suggestions.length > 0 && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-zinc-900 border border-zinc-700 rounded-lg
                              shadow-2xl z-30 max-h-80 overflow-y-auto">
                {suggestions.map((s) => (
                  <Link
                    key={s.steam_id}
                    to={`/player/${s.steam_id}`}
                    onClick={() => setShowDropdown(false)}
                    className="flex items-center gap-2 px-3 py-2 hover:bg-zinc-800 border-b border-zinc-800 last:border-0"
                  >
                    <Avatar url={s.avatar_url} name={s.name} size={28} />
                    <span className="flex-1 text-sm text-zinc-200 truncate">{s.name}</span>
                    <span className="text-xs text-zinc-500 tabular-nums">{s.matches}m</span>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>

        <div>
          <label className="block text-xs text-zinc-400 mb-1">{t('filters.period')}</label>
          <select
            value={period}
            onChange={(e) => onChange({ period: e.target.value as Period })}
            className="bg-zinc-800 text-zinc-100 px-3 py-2 rounded text-sm min-w-[160px]"
          >
            <option value="">{t('filters.allTime')}</option>
            <option value="7d">{t('filters.last7d')}</option>
            <option value="30d">{t('filters.last30d')}</option>
            <option value="90d">{t('filters.last90d')}</option>
          </select>
        </div>

        <div>
          <label className="block text-xs text-zinc-400 mb-1">{t('filters.sideFaction')}</label>
          <select
            value={side}
            onChange={(e) => onChange({ side: e.target.value as Side })}
            className={`px-3 py-2 rounded text-sm min-w-[160px] border ${
              side === 'Allies' || side === 'US' || side === 'GB' || side === 'USSR'
                ? 'bg-blue-900/60 text-blue-100 border-blue-500/50' :
              side === 'Axis' || side === 'Wehrmacht' || side === 'DAK'
                ? 'bg-red-900/60 text-red-100 border-red-500/50' :
              'bg-zinc-800 text-zinc-100 border-transparent'
            }`}
            title={t('filters.factionTooltip')}
          >
            <option value="">{t('filters.any')}</option>
            <optgroup label={t('filters.sideLabel')}>
              <option value="Allies">{t('filters.alliesAll')}</option>
              <option value="Axis">{t('filters.axisAll')}</option>
            </optgroup>
            <optgroup label={t('filters.alliesFaction')}>
              <option value="US">🇺🇸 US</option>
              <option value="GB">🇬🇧 GB / Commonwealth</option>
              <option value="USSR">☭ USSR</option>
            </optgroup>
            <optgroup label={t('filters.axisFaction')}>
              <option value="Wehrmacht">🦅 Wehrmacht</option>
              <option value="DAK">🐪 DAK (Africa)</option>
            </optgroup>
          </select>
        </div>

        <div>
          <label className="block text-xs text-zinc-400 mb-1">{t('filters.mode')}</label>
          <select
            value={gameMode}
            onChange={(e) => onChange({ gameMode: e.target.value as GameMode })}
            className={`px-3 py-2 rounded text-sm min-w-[140px] border ${
              gameMode === 'warfare'   ? 'bg-sky-900/60 text-sky-100 border-sky-500/50' :
              gameMode === 'offensive' ? 'bg-orange-900/60 text-orange-100 border-orange-500/50' :
              gameMode === 'skirmish'  ? 'bg-emerald-900/60 text-emerald-100 border-emerald-500/50' :
              'bg-zinc-800 text-zinc-100 border-transparent'
            }`}
          >
            <option value="">{t('filters.allModes')}</option>
            <option value="warfare">⚔️ Warfare</option>
            <option value="offensive">🗡 Offensive</option>
            <option value="skirmish">🎯 Skirmish</option>
          </select>
        </div>

        <div>
          <label className="block text-xs text-zinc-400 mb-1">{t('filters.map')}</label>
          <select
            value={mapName}
            onChange={(e) => onChange({ mapName: e.target.value })}
            className="bg-zinc-800 text-zinc-100 px-3 py-2 rounded text-sm min-w-[200px]"
          >
            <option value="">{t('filters.allMaps', { count: maps.length })}</option>
            {maps.map((m) => <option key={m} value={m}>{formatMapName(m)}</option>)}
          </select>
        </div>

        <div>
          <label className="block text-xs text-zinc-400 mb-1">{t('filters.weaponClass')}</label>
          <select
            value={weaponClass}
            onChange={(e) => onChange({ weaponClass: e.target.value })}
            className="bg-zinc-800 text-zinc-100 px-3 py-2 rounded text-sm min-w-[180px]"
          >
            <option value="">{t('filters.allClasses')}</option>
            {classes.map((c) => (
              <option key={c.name} value={c.name}>{c.name} ({c.count})</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs text-zinc-400 mb-1">{t('filters.weapon')}</label>
          <select
            value={weapon}
            onChange={(e) => onChange({ weapon: e.target.value })}
            className="bg-zinc-800 text-zinc-100 px-3 py-2 rounded text-sm min-w-[200px]"
          >
            <option value="">{t('filters.allWeapons', { count: weapons.length })}</option>
            {weapons.map((w) => <option key={w} value={w}>{w}</option>)}
          </select>
        </div>

        <div>
          <label className="block text-xs text-zinc-400 mb-1">
            {t('filters.minMatches')}: <span className="text-amber-400 font-bold">{minMatches}</span>
          </label>
          <input
            type="range"
            min={0}
            max={500}
            step={10}
            value={minMatches}
            onChange={(e) => onChange({ minMatches: Number(e.target.value) })}
            className="w-48 accent-amber-500"
          />
        </div>

        {hasActive && (
          <button
            onClick={onReset}
            className="px-3 py-2 rounded bg-zinc-700 hover:bg-zinc-600 text-sm self-end"
            title={t('filters.resetTitle')}
          >{t('filters.reset')}</button>
        )}
      </div>
    </div>
  )
}
