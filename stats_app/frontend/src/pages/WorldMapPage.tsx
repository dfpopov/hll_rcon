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
import { useTranslation } from 'react-i18next'
import { fetchCountries, CountryEntry } from '../api/client'
import CountryFlag from '../components/CountryFlag'
import { ISO_A2_TO_NUMERIC } from '../components/isoCountryCodes'

const TOPO_URL = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json'

// Numeric ISO codes for special-case rendering on the map.
const RU_ID = '643'   // Russia — struck through with diagonal pattern
const UA_ID = '804'   // Ukraine — Crimea overlay also painted in this color

// Crimea boundary polygon (simplified ~20 points). Drawn ON TOP of Russia's
// path so it visually returns to Ukraine, matching internationally
// recognized territorial integrity (UN GA Resolution 68/262).
const CRIMEA_GEOJSON = {
  type: 'FeatureCollection',
  features: [{
    type: 'Feature',
    properties: { name: 'Crimea (UA)' },
    geometry: {
      type: 'Polygon',
      coordinates: [[
        [33.50, 46.20], [34.20, 46.20], [34.90, 46.18], [35.40, 46.10],
        [35.95, 45.60], [36.65, 45.45], [36.55, 45.25], [36.10, 45.00],
        [35.50, 44.95], [35.00, 44.85], [34.50, 44.70], [34.00, 44.55],
        [33.55, 44.45], [33.30, 44.40], [33.00, 44.50], [32.55, 44.85],
        [32.50, 45.20], [32.65, 45.55], [32.85, 45.85], [33.50, 46.20],
      ]],
    },
  }],
} as const

export default function WorldMapPage() {
  const { t, i18n } = useTranslation()
  const numFmt = new Intl.NumberFormat(i18n.resolvedLanguage || i18n.language || 'en')
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
        <h1 className="text-3xl font-bold mb-1">{t('worldMap.title')}</h1>
        <p className="text-zinc-400 text-sm">
          {t('worldMap.subtitle', { players: numFmt.format(totalPlayers), countries: data.length })}
          {hover && (
            <span className="ml-2 text-amber-400">
              • {t('worldMap.hover')}: <CountryFlag iso={hover.a2} showCode /> {numFmt.format(hover.players)}
            </span>
          )}
        </p>
      </header>

      {loading && <div className="text-zinc-400 py-8 text-center">{t('common.loading')}</div>}

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
              {/* SVG patterns: diagonal red strike for Russia, used as fill */}
              <defs>
                <pattern id="ru-strike" patternUnits="userSpaceOnUse" width="6" height="6"
                  patternTransform="rotate(45)">
                  <rect width="6" height="6" fill="#3a1010" />
                  <line x1="0" y1="0" x2="0" y2="6" stroke="#b91c1c" strokeWidth="2" />
                </pattern>
              </defs>
              <Geographies geography={TOPO_URL}>
                {({ geographies }) =>
                  geographies.map((geo) => {
                    const id = geo.id  // numeric ISO string
                    const n = countByNumeric.get(id) ?? 0
                    const isRussia = id === RU_ID
                    const a2 = numericToA2.get(id) ?? (isRussia ? 'RU' : '')
                    // Hover-fill driven by shared state so Crimea and Ukraine
                    // light up together; CSS :hover only affects one element.
                    // Russia is hover-only struck through — looks like a normal
                    // country until pointed at, then reveals the diagonal strike.
                    const isHovered = isRussia ? hover?.a2 === 'RU' : (hover?.a2 === a2 && n > 0)
                    let fill: string
                    if (isRussia && isHovered) fill = 'url(#ru-strike)'
                    else if (isHovered) fill = '#fbbf24'
                    else fill = n > 0 ? colorScale(n) : '#1f1f23'
                    return (
                      <Geography
                        key={geo.rsmKey}
                        geography={geo}
                        fill={fill}
                        stroke={isRussia && isHovered ? '#b91c1c' : '#3f3f46'}
                        strokeWidth={isRussia && isHovered ? 0.5 : 0.3}
                        onMouseEnter={() => {
                          if (isRussia) setHover({ a2: 'RU', players: n })
                          else if (n > 0) setHover({ a2, players: n })
                        }}
                        onMouseLeave={() => setHover(null)}
                        style={{
                          default: { outline: 'none', cursor: n > 0 ? 'pointer' : 'default' },
                          hover: { outline: 'none' },
                          pressed: { outline: 'none' },
                        }}
                      />
                    )
                  })
                }
              </Geographies>
              {/* Crimea overlay — shares Ukraine's hover state so both
                  highlight together when hovered. */}
              <Geographies geography={CRIMEA_GEOJSON as any}>
                {({ geographies }) =>
                  geographies.map((geo) => {
                    const uaCount = countByNumeric.get(UA_ID) ?? 0
                    const uaBaseFill = uaCount > 0 ? colorScale(uaCount) : '#1f1f23'
                    const uaHovered = hover?.a2 === 'UA' && uaCount > 0
                    return (
                      <Geography
                        key={geo.rsmKey}
                        geography={geo}
                        fill={uaHovered ? '#fbbf24' : uaBaseFill}
                        stroke="#3f3f46"
                        strokeWidth={0.3}
                        style={{
                          default: { outline: 'none', cursor: uaCount > 0 ? 'pointer' : 'default' },
                          hover: { outline: 'none' },
                          pressed: { outline: 'none' },
                        }}
                        onMouseEnter={() => uaCount > 0 && setHover({ a2: 'UA', players: uaCount })}
                        onMouseLeave={() => setHover(null)}
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
              <span>{numFmt.format(max)}</span>
            </div>
          </div>

          {/* Top countries list — takes 1/3 */}
          <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4">
            <h2 className="text-zinc-300 uppercase text-xs tracking-widest mb-3">{t('worldMap.topCountries')}</h2>
            <ol className="space-y-1 text-sm max-h-[480px] overflow-y-auto">
              {data.slice(0, 50).map((c, i) => (
                <li key={c.country} className="flex items-center gap-2">
                  <span className="text-zinc-500 w-6 text-right tabular-nums">{i + 1}.</span>
                  <CountryFlag iso={c.country} />
                  <span className="text-zinc-300 flex-1">{c.country}</span>
                  <span className="text-zinc-100 tabular-nums font-medium">{numFmt.format(c.players)}</span>
                  <span className="text-zinc-500 text-xs tabular-nums w-14 text-right">{c.pct}%</span>
                </li>
              ))}
            </ol>
            {data.length > 50 && (
              <div className="text-xs text-zinc-600 mt-2 text-center">
                {t('worldMap.moreCountries', { count: data.length - 50 })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
