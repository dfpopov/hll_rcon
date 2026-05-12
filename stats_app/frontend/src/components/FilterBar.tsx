import { useEffect, useState } from 'react'
import { fetchMaps, fetchWeapons, Period } from '../api/client'

interface FilterBarProps {
  period: Period
  minMatches: number
  weapon: string
  mapName: string
  onChange: (next: {
    period?: Period
    minMatches?: number
    weapon?: string
    mapName?: string
  }) => void
  onReset: () => void
}

export default function FilterBar({
  period, minMatches, weapon, mapName, onChange, onReset,
}: FilterBarProps) {
  const [maps, setMaps] = useState<string[]>([])
  const [weapons, setWeapons] = useState<string[]>([])

  useEffect(() => {
    fetchMaps().then(setMaps).catch(() => {})
    fetchWeapons().then(setWeapons).catch(() => {})
  }, [])

  const hasActive = period || weapon || mapName || minMatches !== 50

  return (
    <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4 mb-4">
      <div className="flex flex-wrap gap-3 items-end">
        <div>
          <label className="block text-xs text-zinc-400 mb-1">Період</label>
          <select
            value={period}
            onChange={(e) => onChange({ period: e.target.value as Period })}
            className="bg-zinc-800 text-zinc-100 px-3 py-2 rounded text-sm min-w-[160px]"
          >
            <option value="">Увесь час</option>
            <option value="7d">Останні 7 днів</option>
            <option value="30d">Останні 30 днів</option>
            <option value="90d">Останні 90 днів</option>
          </select>
        </div>

        <div>
          <label className="block text-xs text-zinc-400 mb-1">Карта</label>
          <select
            value={mapName}
            onChange={(e) => onChange({ mapName: e.target.value })}
            className="bg-zinc-800 text-zinc-100 px-3 py-2 rounded text-sm min-w-[220px]"
          >
            <option value="">Усі карти ({maps.length})</option>
            {maps.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs text-zinc-400 mb-1">Зброя</label>
          <select
            value={weapon}
            onChange={(e) => onChange({ weapon: e.target.value })}
            className="bg-zinc-800 text-zinc-100 px-3 py-2 rounded text-sm min-w-[200px]"
          >
            <option value="">Усе ({weapons.length})</option>
            {weapons.map((w) => (
              <option key={w} value={w}>{w}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs text-zinc-400 mb-1">
            Мін. матчів: <span className="text-amber-400 font-bold">{minMatches}</span>
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
            title="Скинути всі фільтри"
          >
            ✕ Скинути
          </button>
        )}
      </div>
    </div>
  )
}
