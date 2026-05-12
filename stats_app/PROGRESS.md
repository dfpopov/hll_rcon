# stats_app — Progress Log

Live tracker of implementation status. Updates inline as work proceeds.
Architectural decisions live in `PLAN.md`.

## Current phase: **MVP**

## Task status

| ID | Task | Status | Notes |
|---|---|---|---|
| 7 | Backend FastAPI skeleton + /api/top-kills (no filters) | 🟡 in_progress | Creating now |
| 8 | Backend /api/top-kills with filters (period/weapon/map/side) | ⏸ pending | Phase 2 |
| 9 | Backend /api/player/{steam_id} with PVP | ⏸ pending | Phase 3 |
| 10 | Backend /api/maps + /api/weapons | ⏸ pending | Phase 2 |
| 11 | Frontend React+Vite skeleton | ⏸ pending | MVP, next |
| 12 | Frontend HomePage with table & filters | ⏸ pending | Phase 2 |
| 13 | Frontend PlayerDetailPage with PVP heatmap | ⏸ pending | Phase 3 |
| 14 | Docker compose service + nginx + deploy 7012 | ⏸ pending | MVP, next |
| 15 | Investigation: how to derive "side" per player per match | ⏸ pending | Phase 4 blocker |

## Findings (chronological)

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
