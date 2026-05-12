import axios from 'axios'

export const api = axios.create({
  baseURL: '/api',
  timeout: 20000,
})

export type SortKey =
  | 'kills' | 'deaths' | 'teamkills'
  | 'kd_ratio' | 'kpm' | 'playtime' | 'matches' | 'level'
  | 'combat' | 'offense' | 'defense' | 'support'

export type SortOrder = 'asc' | 'desc'
export type Period = '7d' | '30d' | '90d' | ''
export type GameMode = 'warfare' | 'offensive' | 'skirmish' | ''

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
  combat?: number
  offense?: number
  defense?: number
  support?: number
  avatar_url?: string | null
  country?: string | null
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
  game_mode: GameMode | null
  weapon_class: string | null
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
  game_mode?: GameMode
  weapon_class?: string
}

export interface WeaponClass {
  name: string
  count: number
  examples: string[]
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
  if (opts.game_mode) params.game_mode = opts.game_mode
  if (opts.weapon_class) params.weapon_class = opts.weapon_class
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

export async function fetchWeaponClasses(): Promise<WeaponClass[]> {
  const { data } = await api.get<{ classes: WeaponClass[] }>('/weapon-classes')
  return data.classes
}

// --- Phase 3: single-game records ---

export type SingleGameMetric =
  | 'kills' | 'deaths' | 'teamkills'
  | 'combat' | 'support' | 'offense' | 'defense'
  | 'kills_streak' | 'kill_death_ratio' | 'kills_per_minute'

export interface SingleGameRow {
  steam_id: string
  name: string
  level: number
  value: number
  map_name: string
  match_date: string | null
}

export async function fetchBestSingleGame(metric: SingleGameMetric, limit = 10) {
  const { data } = await api.get<{ metric: SingleGameMetric; count: number; results: SingleGameRow[] }>(
    '/best-single-game', { params: { metric, limit } }
  )
  return data
}

// --- Phase 3: player detail ---

export interface PlayerProfile {
  steam_id: string
  name: string
  level: number
  kills: number
  deaths: number
  teamkills: number
  deaths_by_tk: number
  kd_ratio: number | null
  kpm: number | null
  matches_played: number
  total_seconds: number
  combat: number
  offense: number
  defense: number
  support: number
  best_kills_streak: number
  longest_life_secs: number
  avatar_url: string | null
  persona_name: string | null
  profile_url: string | null
  country: string | null
}

export interface Achievement {
  id: string
  title: string
  icon: string
  tier: 'common' | 'uncommon' | 'rare' | 'epic' | 'legendary' | 'mythic'
}

export interface WeaponKills { weapon: string; kills: number }
export interface PvpEntry { victim?: string; killer?: string; kills?: number; deaths?: number }
export interface RecentMatch {
  match_id: number
  map_name: string
  match_date: string | null
  kills: number
  deaths: number
  kd: number | null
  combat: number
  support: number
}

export interface PlayerDetail {
  profile: PlayerProfile
  achievements: Achievement[]
  top_weapons: WeaponKills[]
  most_killed: { victim: string; kills: number }[]
  killed_by: { killer: string; deaths: number }[]
  recent_matches: RecentMatch[]
}

export async function fetchPlayerDetail(steamId: string): Promise<PlayerDetail> {
  const { data } = await api.get<PlayerDetail>(`/player/${encodeURIComponent(steamId)}`)
  return data
}

/**
 * Look up steam_id by player name. Returns null if not found (404).
 * Used to make PVP victim/killer names clickable.
 */
export async function findPlayerByName(name: string): Promise<string | null> {
  try {
    const { data } = await api.get<{ steam_id: string; name: string }>(
      '/player-by-name', { params: { name } }
    )
    return data.steam_id
  } catch {
    return null
  }
}
