/**
 * 24-hour heatmap of a player's match activity. Each cell = one hour of the
 * day. Opacity scales with match count relative to the busiest hour, so the
 * pattern stands out regardless of total volume. Hours with zero activity
 * stay near-empty.
 *
 * Server time is whatever PostgreSQL stores in map_history.start — typically
 * server local time; we render hour labels in 24h format and note the
 * convention. No timezone conversion attempted.
 */
interface Props {
  hours: number[]  // length 24
}

export default function TimeOfDayHeatmap({ hours }: Props) {
  const total = hours.reduce((a, b) => a + b, 0)
  if (total === 0) {
    return <div className="text-zinc-600 text-sm italic">недостатньо матчів для розкладу</div>
  }
  const max = Math.max(...hours)
  const peakHour = hours.indexOf(max)
  const peakCount = max
  const peakPct = (peakCount / total * 100).toFixed(1)

  return (
    <div>
      <div className="grid grid-cols-24 gap-px" style={{ gridTemplateColumns: 'repeat(24, minmax(0, 1fr))' }}>
        {hours.map((n, h) => {
          const intensity = max > 0 ? n / max : 0
          const opacity = intensity === 0 ? 0.08 : 0.2 + intensity * 0.8
          return (
            <div
              key={h}
              className="aspect-square rounded-sm flex items-center justify-center"
              style={{ backgroundColor: `rgba(245, 158, 11, ${opacity})` }}
              title={`${String(h).padStart(2, '0')}:00 — ${n} матчів (${(n / total * 100).toFixed(1)}%)`}
            >
              {n > 0 && intensity > 0.5 && (
                <span className="text-[10px] font-bold text-zinc-900 tabular-nums">{n}</span>
              )}
            </div>
          )
        })}
      </div>
      {/* Hour ruler — every 3 hours to avoid clutter */}
      <div className="grid mt-1" style={{ gridTemplateColumns: 'repeat(24, minmax(0, 1fr))' }}>
        {[0, 3, 6, 9, 12, 15, 18, 21].map((h) => (
          <span
            key={h}
            style={{ gridColumn: `${h + 1} / span 3` }}
            className="text-[10px] text-zinc-600 text-left"
          >{String(h).padStart(2, '0')}</span>
        ))}
      </div>
      <div className="text-xs text-zinc-500 mt-2">
        Пік активності: <span className="text-amber-400 font-medium">{String(peakHour).padStart(2, '0')}:00</span>
        {' '}({peakCount} матчів, {peakPct}% усієї активності)
      </div>
    </div>
  )
}
