# stats_app — All-time HLL Statistics Site

Standalone web application exposing all-time aggregated player statistics
from CRCON's PostgreSQL on **http://95.111.230.75:7012/**.

## Goal

Public read-only site where players (and admins) can browse:
- Top players ranked by various metrics across **all** matches ever played
- Per-player detailed view with PVP relationships ("кого убивал", "кто убивал")
- Filters: time period, weapon, map, side (faction)
- Future: Cloudflare domain (e.g., `stats.<your-domain>`)

## Architecture

```
stats_app/
├── backend/                  FastAPI service (Python)
│   ├── main.py               app entry, CORS, routes
│   ├── db.py                 SQLAlchemy session, connects to CRCON Postgres
│   ├── queries.py            SQL aggregations
│   ├── schemas.py            Pydantic response models
│   ├── routes/               per-resource routers
│   │   ├── top_kills.py
│   │   ├── player.py
│   │   ├── maps.py
│   │   └── weapons.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                 React + Vite + TypeScript + Tailwind
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── pages/
│   │   │   ├── HomePage.tsx       top table + filters
│   │   │   └── PlayerDetail.tsx   pvp + weapons + matches
│   │   ├── components/
│   │   │   ├── PlayersTable.tsx
│   │   │   ├── FilterBar.tsx
│   │   │   └── PvpList.tsx
│   │   └── api/client.ts          axios instance
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   └── Dockerfile                  multi-stage: vite build → nginx alpine
├── Dockerfile                 final image: nginx + uvicorn via supervisord
├── nginx.conf                 proxies /api/* → backend, / → static files
├── supervisord.conf           manages both nginx and uvicorn
├── PLAN.md                    this file
└── PROGRESS.md                live progress tracking

compose.yaml adds:
  stats_app:
    build: ./stats_app
    ports:
      - "7012:80"
    environment:
      DATABASE_URL: postgres://rcon:${HLL_DB_PASSWORD}@postgres:5432/rcon
```

## API endpoints

| Method | Endpoint | Params | Purpose |
|---|---|---|---|
| GET | `/api/health` | — | Liveness probe |
| GET | `/api/top-kills` | `limit` (50), `period` (all/30d/7d), `weapon?`, `map_id?`, `side?` | Top-N players ranked by kills |
| GET | `/api/player/{steam_id}` | — | Per-player stats + PVP + weapons + matches |
| GET | `/api/maps` | — | All maps for dropdown |
| GET | `/api/weapons` | — | All unique weapons for dropdown |
| GET | `/api/sides` | — | List of factions (after Task #15) |

## Data sources (CRCON PostgreSQL)

| Table | Use |
|---|---|
| `player_stats` | Per-match per-player K/D/TK/weapons/most_killed/death_by |
| `steam_id_64` | player_id <→ DB id mapping |
| `map_history` | Match metadata (map name, date) |
| `players` | Player names |

**Side filter** is blocked on Task #15 investigation — `player_stats` does not
record which faction the player was on per match. Possible sources: parse from
`game_logs` (CHAT[Allies]/CHAT[Axis]), or hardcode per-map faction matrix
(Stalingrad → USSR vs GER, El Alamein → UK vs DAK, etc.).

## Phases

| Phase | Scope | Tasks |
|---|---|---|
| **MVP** | Backend skeleton + 1 endpoint `/api/top-kills` (no filters) + frontend skeleton with one page (top-kills table) + deploy on :7012 | 7, 11, 14 |
| **Phase 2** | Filters: period, weapon, map | 8, 10, 12 |
| **Phase 3** | Player detail page with PVP | 9, 13 |
| **Phase 4** | Side filter (requires investigation) | 15, 8, 12 |
| **Future** | Cloudflare DNS + Caddy HTTPS, multi-server aggregation if more servers added | — |

## Security / non-functional

- **Read-only DB user**: production should create `rcon_readonly` Postgres role
  with `GRANT SELECT ON ALL TABLES` only, configured via env in compose.yaml.
  MVP can use existing `rcon` user; tightening is a follow-up task.
- **CORS**: backend allows only `http://95.111.230.75:7012` initially; extend
  when adding Cloudflare domain.
- **Caching**: not needed for MVP (existing indexes on playersteamid_id/map_id
  give ms-level queries for current data volume).
- **Auth**: NONE — public read-only site. If admins later want
  IP-restricted analytics views, add nginx basic auth on specific routes.

## Non-goals (out of scope)

- Writing to CRCON DB (read-only)
- Real-time websocket updates (HTTP polling sufficient)
- Mobile native apps (responsive web)
- Account system (anyone can browse)

## Findings & changes log

Updates flow into `PROGRESS.md`. Architectural changes (e.g., switching from
React to Vue, adding caching layer) update THIS file with a dated revision
note at the bottom.
