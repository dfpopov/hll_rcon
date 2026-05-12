/**
 * Hexagonal radar chart of a player's 6 skill axes, normalized vs hand-picked
 * "good player" reference thresholds. Each axis is capped at 100 (so an
 * exceptional player doesn't deform the chart).
 */
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip,
} from 'recharts'
import { PlayerProfile } from '../api/client'

interface AxisDef {
  key: string
  label: string
  /** Player value divided by ref → 0..1 (clamped 0..1.2 then ×100). */
  ref: number
  get: (p: PlayerProfile) => number
}

// Per-axis reference (~p95 of active player base; tweak by feel)
const AXES: AxisDef[] = [
  { key: 'kpm',     label: 'KPM',          ref: 2.0,  get: (p) => p.kpm ?? 0 },
  { key: 'kd',      label: 'K/D',          ref: 3.0,  get: (p) => p.kd_ratio ?? 0 },
  { key: 'combat',  label: 'Combat/мін',   ref: 10,   get: (p) => p.combat  / Math.max(1, p.total_seconds / 60) },
  { key: 'support', label: 'Support/мін',  ref: 30,   get: (p) => p.support / Math.max(1, p.total_seconds / 60) },
  { key: 'offense', label: 'Offense/мін',  ref: 5,    get: (p) => p.offense / Math.max(1, p.total_seconds / 60) },
  { key: 'defense', label: 'Defense/мін',  ref: 10,   get: (p) => p.defense / Math.max(1, p.total_seconds / 60) },
]

export default function PlayerRadar({ p }: { p: PlayerProfile }) {
  const data = AXES.map((a) => {
    const v = a.get(p)
    const pct = Math.min(120, (v / a.ref) * 100)  // cap at 120 to avoid blowing out
    return { axis: a.label, value: pct, raw: v }
  })

  return (
    <ResponsiveContainer width="100%" height={280}>
      <RadarChart data={data} outerRadius="80%">
        <PolarGrid stroke="#3f3f46" />
        <PolarAngleAxis dataKey="axis" tick={{ fill: '#a1a1aa', fontSize: 11 }} />
        <PolarRadiusAxis domain={[0, 120]} tick={false} axisLine={false} />
        <Tooltip
          contentStyle={{ backgroundColor: '#18181b', border: '1px solid #3f3f46', fontSize: 12 }}
          labelStyle={{ color: '#f4f4f5' }}
          formatter={(_value, _name, props) => {
            const d = props?.payload
            if (!d) return ['', '']
            return [`${d.raw.toFixed(2)} (${Math.round(d.value)}% від еталону)`, d.axis]
          }}
        />
        <Radar name="player" dataKey="value" stroke="#f59e0b" fill="#f59e0b" fillOpacity={0.35} />
      </RadarChart>
    </ResponsiveContainer>
  )
}
