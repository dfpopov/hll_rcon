# stats_app — Progress Log

Live tracker of implementation status. Updates inline as work proceeds.
Architectural decisions live in `PLAN.md`.

## Current phase: **Phase 3 ✅ DEPLOYED** — http://95.111.230.75:7012/

Pages live:
- `/` — leaderboard with 7 filters (search, period, mode, map, weapon class,
  specific weapon, min matches) + sortable columns + pagination
- `/records` — hllrecords-style grid of mini-leaderboards (10 all-time + 8 single-game)
- `/player/{steam_id}` — per-player profile with PVP heatmap (most killed, killed by, weapons)

## Task status

| ID | Task | Status | Notes |
|---|---|---|---|
| 7 | Backend FastAPI skeleton + /api/top-kills (no filters) | ✅ completed | `/api/health` + `/api/top-kills?limit=50` live |
| 8 | Backend /api/top-kills with filters (period/weapon/map/side) | ⏸ pending | Phase 2 |
| 9 | Backend /api/player/{steam_id} with PVP | ⏸ pending | Phase 3 |
| 10 | Backend /api/maps + /api/weapons | ⏸ pending | Phase 2 |
| 11 | Frontend React+Vite skeleton | ✅ completed | Vite+TS+Tailwind, top-50 table page |
| 12 | Frontend HomePage with table & filters | ⏸ pending | Phase 2 |
| 13 | Frontend PlayerDetailPage with PVP heatmap | ⏸ pending | Phase 3 |
| 14 | Docker compose service + nginx + deploy 7012 | ✅ completed | container Up, supervisord runs nginx+uvicorn |
| 15 | Investigation: how to derive "side" per player per match | ⏸ pending | Phase 4 blocker |

## Findings (chronological)

### 2026-05-12 — Phase 2 progress: sort + pagination + rate limit

- Renamed `/api/top-kills` → `/api/top-players`. Single endpoint now serves
  sortable leaderboard for **all** columns (kills/deaths/teamkills/kd_ratio/
  kpm/playtime/matches/level), making top-playtime a special case of
  top-players?sort=playtime — no separate endpoint needed.
- **Whitelisted SQL ORDER BY**: SORT_COLUMNS dict in queries.py maps API
  param to SQL expression. Prevents SQL injection through the sort param.
- **Pagination**: limit (1-100, default 50) + offset (>=0). Response also
  includes `total` from `COUNT(DISTINCT playersteamid_id)` so frontend
  can render "page X of Y" controls.
- **Rate limiting**: slowapi middleware, 60 req/min/IP default, in-memory.
  `/api/health` excluded. If load grows, migrate to Redis-based.
- **Level prominence**: gradient badges colored by tier (zinc→emerald→amber
  →orange→red as level climbs, max class for L250+). Sits before player name.
- **Active-sort highlight**: column header turns amber when sort matches,
  row cell of that column also amber+bold. Easy to see what's being ranked.
- **Sample numbers** (limit=3, sort=playtime):
  Use http://95.111.230.75:7012/api/top-players?sort=playtime to see who
  has spent the most time in matches.

### 2026-05-12 — MVP deployed (port 7012)

- Successfully built and ran `stats_app` container (~67s docker build).
- First deploy crashed: `nginx.conf` had `user nginx;` directive but
  python:3.12-slim base image has no `nginx` system user. Fixed by
  removing the directive (nginx runs as root in container — standard
  pattern for single-process containers). +12 lines patch in nginx.conf
  and supervisord.conf (also added [supervisorctl] socket section for
  debugging).
- Sanity-checked endpoints:
  - GET /api/health → HTTP 200 `{"status":"ok",...}`
  - GET /api/top-kills?limit=3 → HTTP 200 with real player data
  - GET / → HTTP 200 React app HTML
- **Sample data** (top by kills, all-time):
  - Heartattack333: K=6302 D=3464 K/D=1.82 in 392 matches
  - Пакет с пакетами: K=5958 D=6016 K/D=0.99 in 865 matches
  - BaNnY: K=5339 D=2675 K/D=2.00 in 355 matches
- **Potential Phase 2+ addition**: `total_seconds` is already in the API
  response — could power a "Top playtime" leaderboard (Пакет с пакетами
  has 1 904 668 sec ≈ 530 hours of game time, very useful metric).

### 2026-05-12 — Project kickoff

- **CRCON public stats site already exists** at port 7010 (`rcongui_public`),
  but per user it shows only current-match stats, not all-time aggregation.
  Decision: build separate `stats_app` rather than extending `rcongui_public`,
  to keep ElG/MarechJ upgrade compatibility intact.
- **player_stats table has all the data needed**: kills, deaths, K/D, KPM,
  weapons (JSONB), most_killed (JSONB), death_by (JSONB), level, time_seconds.
  No "side" column — see Task #15.
- **Map name lookup**: `player_stats.map_id` → `map_history.id`.
  `map_history` table holds the canonical match record.
- **Postgres connection**: backend will connect via existing CRCON Postgres
  service in docker-compose network (`postgres:5432`).

## Open questions / blockers

- **Side filter (Task #15)**: how to determine player's faction per match?
  Options: parse from event logs, hardcode per-map mapping, query
  team_view at match end and persist. Decision deferred — Phase 4.
- **Read-only DB user**: deferred to follow-up commit after MVP works.

## Decisions taken

- **Tech stack**: FastAPI (Python) backend + React + Vite + Tailwind frontend.
  User confirmed in question dialog.
- **Single docker container**: nginx + uvicorn via supervisord, port 7012:80.
  Simpler than two containers for the same logical app.
- **MVP filters none**: ship `/api/top-kills` without filters first.
  Filters arrive in Phase 2 (Task #8, #10, #12).
- **Side filter deferred** to Phase 4 — investigation required, can't be
  done blind.
