import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  fetchTopPlayers, fetchBestSingleGame,
  PlayerRow, SingleGameRow, SortKey, SingleGameMetric,
} from '../api/client'

interface ShameCardDef {
  key: string
  title: string
  emoji: string
  // Either an aggregate (top players) or a single-game record.
  mode: 'aggregate' | 'single_game'
  sort?: SortKey
  metric?: SingleGameMetric
  order?: 'asc' | 'desc'
  min_matches?: number
  valueFmt?: (r: any) => string | number
  caption: string  // explanation shown under the title
}

const CRCON_PUBLIC_BASE = 'http://95.111.230.75:7010'

const SHAME_CARDS: ShameCardDef[] = [
  {
    key: 'tk_total',
    title: 'Найбільше TK за весь час',
    emoji: '🤡',
    mode: 'aggregate',
    sort: 'teamkills',
    valueFmt: (r: PlayerRow) => r.teamkills.toLocaleString('uk-UA'),
    caption: 'Шкільні стрільці. Своїх вбили більше, ніж усі решта.',
  },
  {
    key: 'tk_victims',
    title: 'Найбільше смертей від ТК своїх',
    emoji: '😅',
    mode: 'aggregate',
    sort: 'deaths_by_tk',
    valueFmt: (r: PlayerRow) => (r.deaths_by_tk ?? 0).toLocaleString('uk-UA'),
    caption: 'Завжди не там стоять. Магніт для союзницьких куль.',
  },
  {
    key: 'worst_kd',
    title: 'Найгірший K/D з 100+ матчами',
    emoji: '📉',
    mode: 'aggregate',
    sort: 'kd_ratio',
    order: 'asc',
    min_matches: 100,
    valueFmt: (r: PlayerRow) => r.kd_ratio ?? '—',
    caption: 'Грали довго, грали постійно. Стріляти так і не навчилися.',
  },
  {
    key: 'most_deaths',
    title: 'Найбільше смертей за весь час',
    emoji: '🪦',
    mode: 'aggregate',
    sort: 'deaths',
    valueFmt: (r: PlayerRow) => r.deaths.toLocaleString('uk-UA'),
    caption: 'Кожен матч — нова сторінка некролога.',
  },
  {
    key: 'worst_game_deaths',
    title: 'Найгірший матч за смертями',
    emoji: '💩',
    mode: 'single_game',
    metric: 'deaths',
    caption: 'Один матч — одна катастрофа. 70+ смертей за гру — це треба ще постаратися.',
  },
  {
    key: 'worst_game_tk',
    title: 'Найбільше TK в одному матчі',
    emoji: '☠️',
    mode: 'single_game',
    metric: 'teamkills',
    caption: 'Команді потрібен капітан. А прийшов он — з гранатами.',
  },
]

function PlayerLine({ rank, name, steam_id, value }: { rank: number; name: string; steam_id: string; value: string | number }) {
  return (
    <li className="flex items-baseline gap-2 text-sm">
      <span className="text-zinc-500 w-5 text-right">{rank}.</span>
      <Link to={`/player/${steam_id}`} className="flex-1 truncate hover:text-rose-300 transition-colors" title={name}>
        {name}
      </Link>
      <span className="font-bold text-rose-300 tabular-nums">{value}</span>
    </li>
  )
}

function SingleGameLine({ rank, row }: { rank: number; row: SingleGameRow }) {
  return (
    <li className="flex items-baseline gap-2 text-sm">
      <span className="text-zinc-500 w-5 text-right">{rank}.</span>
      <div className="flex-1 min-w-0">
        <Link to={`/player/${row.steam_id}`} className="hover:text-rose-300 transition-colors block truncate">
          {row.name}
        </Link>
        <a href={`${CRCON_PUBLIC_BASE}/games/${row.match_id}`} target="_blank" rel="noopener noreferrer"
          className="text-xs text-zinc-500 hover:text-amber-400">
          {row.map_name}
        </a>
      </div>
      <span className="font-bold text-rose-300 tabular-nums">{row.value.toLocaleString('uk-UA')}</span>
    </li>
  )
}

function ShameCard({ def }: { def: ShameCardDef }) {
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
        <h3 className="font-semibold text-rose-200 text-sm uppercase tracking-wide flex-1">{def.title}</h3>
      </div>
      <p className="text-xs text-zinc-500 italic mb-3 leading-snug">{def.caption}</p>
      <ol className="space-y-1">
        {loading && <li className="text-zinc-600 text-xs italic">завантаження…</li>}
        {!loading && rows.length === 0 && <li className="text-zinc-600 text-xs italic">немає кандидатів</li>}
        {!loading && def.mode === 'aggregate' && (rows as PlayerRow[]).map((r, i) => (
          <PlayerLine key={r.steam_id} rank={i + 1} name={r.name} steam_id={r.steam_id} value={def.valueFmt!(r)} />
        ))}
        {!loading && def.mode === 'single_game' && (rows as SingleGameRow[]).map((r, i) => (
          <SingleGameLine key={`${r.steam_id}-${i}`} rank={i + 1} row={r} />
        ))}
      </ol>
    </div>
  )
}

export default function HallOfShamePage() {
  return (
    <div className="max-w-7xl mx-auto p-6">
      <header className="mb-6">
        <h1 className="text-3xl font-bold mb-1">💀 Hall of Shame</h1>
        <p className="text-zinc-400 text-sm">
          Антиподи лідерборду. Хто стріляє у своїх, гине на ровному місці, і чому ти ніколи не хочеш бути в одному загоні з ними.
        </p>
      </header>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {SHAME_CARDS.map((def) => <ShameCard key={def.key} def={def} />)}
      </div>
    </div>
  )
}
