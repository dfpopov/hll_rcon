/**
 * Sparkline of K/D over recent matches (oldest left → newest right).
 * Reads RecentMatch[] from /api/player; tolerant of empty / single-point input.
 */
import { Line, LineChart, ResponsiveContainer, Tooltip, ReferenceLine } from 'recharts'
import { RecentMatch } from '../api/client'

export default function ProgressionSparkline({ matches }: { matches: RecentMatch[] }) {
  if (!matches || matches.length < 2) {
    return <div className="text-zinc-600 text-xs italic">недостатньо матчів для тренду</div>
  }
  // recent_matches is newest-first; reverse for left=old, right=new.
  const data = [...matches].reverse().map((m, i) => ({
    n: i + 1,
    kd: m.kd ?? 0,
    map: m.map_name,
    date: m.match_date,
  }))

  return (
    <ResponsiveContainer width="100%" height={120}>
      <LineChart data={data} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
        <ReferenceLine y={1} stroke="#52525b" strokeDasharray="3 3" />
        <Tooltip
          contentStyle={{ backgroundColor: '#18181b', border: '1px solid #3f3f46', fontSize: 12 }}
          labelStyle={{ color: '#f4f4f5' }}
          formatter={(value) => {
            const v = typeof value === 'number' ? value : Number(value ?? 0)
            return [v.toFixed(2), 'K/D'] as [string, string]
          }}
          labelFormatter={(_label, payload) => {
            const d = (payload as any)?.[0]?.payload
            if (!d) return ''
            return `${d.map} • ${d.date ? new Date(d.date).toLocaleDateString('uk-UA') : ''}`
          }}
        />
        <Line
          type="monotone"
          dataKey="kd"
          stroke="#f59e0b"
          strokeWidth={2}
          dot={{ fill: '#f59e0b', r: 3 }}
          activeDot={{ r: 5 }}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
