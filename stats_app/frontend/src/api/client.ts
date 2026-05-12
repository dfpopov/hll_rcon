import axios from 'axios'

// Same-origin in production (nginx proxies /api/* → backend),
// uses Vite dev-server proxy in development.
export const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

export type SortKey =
  | 'kills'
  | 'deaths'
  | 'teamkills'
  | 'kd_ratio'
  | 'kpm'
  | 'playtime'
  | 'matches'
  | 'level'

export type SortOrder = 'asc' | 'desc'

export interface PlayerRow {
  steam_id: string
  name: string
  level: number
  kills: number
  deaths: number
  teamkills: number
  kd_ratio: number | null
  kpm: number | null
  matches_played: number
  total_seconds: number
}

export interface TopPlayersResponse {
  count: number
  total: number
  limit: number
  offset: number
  sort: SortKey
  order: SortOrder
  results: PlayerRow[]
}

export async function fetchTopPlayers(opts: {
  sort?: SortKey
  order?: SortOrder
  limit?: number
  offset?: number
} = {}): Promise<TopPlayersResponse> {
  const { data } = await api.get<TopPlayersResponse>('/top-players', {
    params: {
      sort: opts.sort ?? 'kills',
      order: opts.order ?? 'desc',
      limit: opts.limit ?? 50,
      offset: opts.offset ?? 0,
    },
  })
  return data
}
