import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  fetchTopPlayers, fetchBestSingleGame,
  PlayerRow, SingleGameRow, SortKey, SingleGameMetric,
} from '../api/client'
import MiniCompareButton from '../components/MiniCompareButton'
import { formatMapName } from '../components/mapNames'

interface ShameCardDef {
  key: string  // also used as the i18n suffix under `shame.cards.<key>.*`
  emoji: string
  // Either an aggregate (top players) or a single-game record.
  mode: 'aggregate' | 'single_game'
  sort?: SortKey
  metric?: SingleGameMetric
  order?: 'asc' | 'desc'
  min_matches?: number
  // valueFmt receives a locale-aware number formatter so display stays
  // i18n-consistent (e.g. "1 234" in uk, "1,234" in en, "1.234" in de).
  valueFmt?: (r: any, nf: Intl.NumberFormat) => string | number
}

const CRCON_PUBLIC_BASE = 'http://95.111.230.75:7010'

const SHAME_CARDS: ShameCardDef[] = [
  { key: 'tk_total',         emoji: '🤡', mode: 'aggregate',   sort: 'teamkills',    valueFmt: (r: PlayerRow, nf) => nf.format(r.teamkills) },
  { key: 'tk_victims',       emoji: '😅', mode: 'aggregate',   sort: 'deaths_by_tk', valueFmt: (r: PlayerRow, nf) => nf.format(r.deaths_by_tk ?? 0) },
  { key: 'worst_kd',         emoji: '📉', mode: 'aggregate',   sort: 'kd_ratio', order: 'asc', min_matches: 100, valueFmt: (r: PlayerRow) => r.kd_ratio ?? '—' },
  { key: 'most_deaths',      emoji: '🪦', mode: 'aggregate',   sort: 'deaths',       valueFmt: (r: PlayerRow, nf) => nf.format(r.deaths) },
  { key: 'worst_game_deaths', emoji: '💩', mode: 'single_game', metric: 'deaths' },
  { key: 'worst_game_tk',    emoji: '☠️', mode: 'single_game', metric: 'teamkills' },
]

function PlayerLine({ rank, name, steam_id, value }: { rank: number; name: string; steam_id: string; value: string | number }) {
  return (
    <li className="flex items-baseline gap-2 text-sm">
      <span className="text-zinc-500 w-5 text-right">{rank}.</span>
      <Link to={`/player/${steam_id}`} className="flex-1 truncate hover:text-rose-300 transition-colors" title={name}>
        {name}
      </Link>
      <MiniCompareButton steam_id={steam_id} name={name} />
      <span className="font-bold text-rose-300 tabular-nums">{value}</span>
    </li>
  )
}

function SingleGameLine({ rank, row, nf }: { rank: number; row: SingleGameRow; nf: Intl.NumberFormat }) {
  return (
    <li className="flex items-baseline gap-2 text-sm">
      <span className="text-zinc-500 w-5 text-right">{rank}.</span>
      <div className="flex-1 min-w-0">
        <Link to={`/player/${row.steam_id}`} className="hover:text-rose-300 transition-colors block truncate">
          {row.name}
        </Link>
        <a href={`${CRCON_PUBLIC_BASE}/games/${row.match_id}`} target="_blank" rel="noopener noreferrer"
          className="text-xs text-zinc-500 hover:text-amber-400" title={row.map_name}>
          {formatMapName(row.map_name)}
        </a>
      </div>
      <MiniCompareButton steam_id={row.steam_id} name={row.name} />
      <span className="font-bold text-rose-300 tabular-nums">{nf.format(row.value)}</span>
    </li>
  )
}

function ShameCard({ def }: { def: ShameCardDef }) {
  const { t, i18n } = useTranslation()
  const nf = new Intl.NumberFormat(i18n.resolvedLanguage || i18n.language || 'en')
  const [rows, setRows] = useState<PlayerRow[] | SingleGameRow[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    const p = def.mode === 'aggregate'
      ? fetchTopPlayers({
          sort: def.sort,
          order: def.order ?? 'desc',
          limit: 10,
          min_matches: def.min_matches ?? 0,
        }).then((r) => r.results)
      : fetchBestSingleGame(def.metric!, 10).then((r) => r.results)
    p.then((rs) => setRows(rs as any)).finally(() => setLoading(false))
  }, [def.key])  // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="bg-gradient-to-br from-zinc-900 to-rose-950/30 border border-rose-900/40 rounded-lg p-4">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-2xl">{def.emoji}</span>
        <h3 className="font-semibold text-rose-200 text-sm uppercase tracking-wide flex-1">{t(`shame.cards.${def.key}.title`)}</h3>
      </div>
      <p className="text-xs text-zinc-500 italic mb-3 leading-snug">{t(`shame.cards.${def.key}.caption`)}</p>
      <ol className="space-y-1">
        {loading && <li className="text-zinc-600 text-xs italic">{t('common.loading')}</li>}
        {!loading && rows.length === 0 && <li className="text-zinc-600 text-xs italic">{t('shame.noCandidates')}</li>}
        {!loading && def.mode === 'aggregate' && (rows as PlayerRow[]).map((r, i) => (
          <PlayerLine key={r.steam_id} rank={i + 1} name={r.name} steam_id={r.steam_id} value={def.valueFmt!(r, nf)} />
        ))}
        {!loading && def.mode === 'single_game' && (rows as SingleGameRow[]).map((r, i) => (
          <SingleGameLine key={`${r.steam_id}-${i}`} rank={i + 1} row={r} nf={nf} />
        ))}
      </ol>
    </div>
  )
}

export default function HallOfShamePage() {
  const { t } = useTranslation()
  return (
    <div className="max-w-7xl mx-auto p-6">
      <header className="mb-6">
        <h1 className="text-3xl font-bold mb-1">{t('shame.title')}</h1>
        <p className="text-zinc-400 text-sm">{t('shame.subtitle')}</p>
      </header>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {SHAME_CARDS.map((def) => <ShameCard key={def.key} def={def} />)}
      </div>
    </div>
  )
}
