/**
 * Server-wide country distribution as a world choropleth + ranked list.
 *
 * Map: react-simple-maps + world-atlas TopoJSON (loaded from jsdelivr CDN).
 * Each country is fill-coloured on a linear scale from zinc to amber based
 * on its player count. Hovering changes fill to a hot amber. Countries
 * with zero players stay dark.
 */
import { useEffect, useMemo, useState } from 'react'
import { ComposableMap, Geographies, Geography } from 'react-simple-maps'
import { scaleLinear } from 'd3-scale'
import { fetchCountries, CountryEntry } from '../api/client'
import CountryFlag from '../components/CountryFlag'
import { ISO_A2_TO_NUMERIC } from '../components/isoCountryCodes'

const TOPO_URL = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json'

export default function WorldMapPage() {
  const [data, setData] = useState<CountryEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [hover, setHover] = useState<{ a2: string; players: number } | null>(null)

  useEffect(() => {
    setLoading(true)
    fetchCountries()
      .then(setData)
      .finally(() => setLoading(false))
  }, [])

  const { countByNumeric, max, totalPlayers, numericToA2 } = useMemo(() => {
    const byNum: Map<string, number> = new Map()
    const num2a2: Map<string, string> = new Map()
    for (const c of data) {
      const num = ISO_A2_TO_NUMERIC[c.country.toUpperCase()]
      if (num) {
        byNum.set(num, c.players)
        num2a2.set(num, c.country.toUpperCase())
      }
    }
    return {
      countByNumeric: byNum,
      max: Math.max(1, ...data.map((d) => d.players)),
      totalPlayers: data.reduce((s, d) => s + d.players, 0),
      numericToA2: num2a2,
    }
  }, [data])

  const colorScale = scaleLinear<string>().domain([0, max]).range(['#27272a', '#f59e0b'])

  return (
    <div className="max-w-7xl mx-auto p-6">
      <header className="mb-6">
        <h1 className="text-3xl font-bold mb-1">🌍 Гравці зі світу</h1>
        <p className="text-zinc-400 text-sm">
          {totalPlayers.toLocaleString('uk-UA')} гравців з відомою країною • {data.length} країн
          {hover && (
            <span className="ml-2 text-amber-400">
              • Hover: <CountryFlag iso={hover.a2} showCode /> {hover.players.toLocaleString('uk-UA')}
            </span>
          )}
        </p>
      </header>

      {loading && <div className="text-zinc-400 py-8 text-center">Завантаження…</div>}

      {!loading && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Map — takes 2/3 on lg+ */}
          <div className="lg:col-span-2 bg-zinc-900/60 border border-zinc-800 rounded-lg p-2 overflow-hidden">
            <ComposableMap
              projectionConfig={{ scale: 145 }}
              width={800}
              height={420}
              style={{ width: '100%', height: 'auto' }}
            >
              <Geographies geography={TOPO_URL}>
                {({ geographies }) =>
                  geographies.map((geo) => {
                    const id = geo.id  // numeric ISO string
                    const n = countByNumeric.get(id) ?? 0
                    const a2 = numericToA2.get(id) ?? ''
                    return (
                      <Geography
                        key={geo.rsmKey}
                        geography={geo}
                        fill={n > 0 ? colorScale(n) : '#1f1f23'}
                        stroke="#3f3f46"
                        strokeWidth={0.3}
                        onMouseEnter={() => n > 0 && setHover({ a2, players: n })}
                        onMouseLeave={() => setHover(null)}
                        style={{
                          default: { outline: 'none' },
                          hover: { fill: '#fbbf24', outline: 'none', cursor: n > 0 ? 'pointer' : 'default' },
                          pressed: { outline: 'none' },
                        }}
                      />
                    )
                  })
                }
              </Geographies>
            </ComposableMap>
            {/* Colour legend */}
            <div className="flex items-center justify-center gap-2 mt-2 text-xs text-zinc-500">
              <span>0</span>
              <div className="h-2 w-48 rounded" style={{ background: 'linear-gradient(to right, #27272a, #f59e0b)' }} />
              <span>{max.toLocaleString('uk-UA')}</span>
            </div>
          </div>

          {/* Top countries list — takes 1/3 */}
          <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4">
            <h2 className="text-zinc-300 uppercase text-xs tracking-widest mb-3">Топ країн</h2>
            <ol className="space-y-1 text-sm max-h-[480px] overflow-y-auto">
              {data.slice(0, 50).map((c, i) => (
                <li key={c.country} className="flex items-center gap-2">
                  <span className="text-zinc-500 w-6 text-right tabular-nums">{i + 1}.</span>
                  <CountryFlag iso={c.country} />
                  <span className="text-zinc-300 flex-1">{c.country}</span>
                  <span className="text-zinc-100 tabular-nums font-medium">{c.players.toLocaleString('uk-UA')}</span>
                  <span className="text-zinc-500 text-xs tabular-nums w-14 text-right">{c.pct}%</span>
                </li>
              ))}
            </ol>
            {data.length > 50 && (
              <div className="text-xs text-zinc-600 mt-2 text-center">
                +{data.length - 50} інших країн
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
