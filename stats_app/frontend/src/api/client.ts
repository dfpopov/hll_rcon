import axios from 'axios'

export const api = axios.create({
  baseURL: '/api',
  timeout: 20000,
})

export type SortKey =
  | 'kills' | 'deaths' | 'teamkills'
  | 'kd_ratio' | 'kpm' | 'playtime' | 'matches' | 'level'

export type SortOrder = 'asc' | 'desc'
export type Period = '7d' | '30d' | '90d' | ''  // empty = all-time

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
  min_matches: number
  period: Period | null
  weapon: string | null
  map_name: string | null
  search: string | null
  results: PlayerRow[]
}

export interface TopPlayersFilters {
  sort?: SortKey
  order?: SortOrder
  limit?: number
  offset?: number
  min_matches?: number
  period?: Period
  weapon?: string
  map_name?: string
  search?: string
}

export async function fetchTopPlayers(opts: TopPlayersFilters = {}): Promise<TopPlayersResponse> {
  const params: Record<string, string | number> = {
    sort: opts.sort ?? 'kills',
    order: opts.order ?? 'desc',
    limit: opts.limit ?? 50,
    offset: opts.offset ?? 0,
    min_matches: opts.min_matches ?? 50,
  }
  if (opts.period) params.period = opts.period
  if (opts.weapon) params.weapon = opts.weapon
  if (opts.map_name) params.map_name = opts.map_name
  if (opts.search && opts.search.trim().length >= 2) params.search = opts.search.trim()
  const { data } = await api.get<TopPlayersResponse>('/top-players', { params })
  return data
}

export async function fetchMaps(): Promise<string[]> {
  const { data } = await api.get<{ maps: string[] }>('/maps')
  return data.maps
}

export async function fetchWeapons(): Promise<string[]> {
  const { data } = await api.get<{ weapons: string[] }>('/weapons')
  return data.weapons
}
