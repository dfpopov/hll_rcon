import axios from 'axios'

// Same-origin in production (nginx proxies /api/* → backend),
// uses Vite dev-server proxy in development.
export const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

export interface TopKillsRow {
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

export interface TopKillsResponse {
  count: number
  results: TopKillsRow[]
}

export async function fetchTopKills(limit = 50): Promise<TopKillsResponse> {
  const { data } = await api.get<TopKillsResponse>('/top-kills', { params: { limit } })
  return data
}
