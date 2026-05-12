# stats_app — Progress Log

Live tracker of implementation status. Updates inline as work proceeds.
Architectural decisions live in `PLAN.md`.

## Current phase: **Phase 5 ✅ DEPLOYED** — http://95.111.230.75:7012/

Pages live:
- `/` — leaderboard with 8 filters (search, period, mode, map, weapon class,
  specific weapon, min matches, **side**) + sortable columns + pagination
- `/records/all-time` and `/records/single-game` — split records grid with
  expand cards, weapon class leaderboards, side filter, search
- `/achievements` — rarity-sorted grid; `/achievements/{id}` — paginated holders
- `/compare/{id1}/{id2}` — side-by-side stat table + **head-to-head card** +
  top-3 weapons + achievement badges
- `/player/{steam_id}` — profile with PVP, achievements, recent matches (filtered
  to skip K=0 ∧ D≤1 noise), country flag, ⚖ Порівняти button

## Task status

| ID | Task | Status | Notes |
|---|---|---|---|
| 7  | Backend FastAPI skeleton + /api/top-kills | ✅ done | |
| 8  | /api/top filters (period/weapon/map/side) | ✅ done | side filter Phase 1 deployed via player_match_side MV |
| 9  | Backend /api/player/{steam_id} with PVP | ✅ done | |
| 10 | /api/maps + /api/weapons + /api/weapon-classes | ✅ done | |
| 11 | Frontend Vite skeleton | ✅ done | |
| 12 | HomePage + FilterBar | ✅ done | search + side + period + mode + map + class + weapon + min_matches |
| 13 | PlayerDetailPage with PVP | ✅ done | |
| 14 | Docker compose deploy 7012 | ✅ done | |
| 15 | Side per (player, match) — investigation | ✅ resolved | regex on log_lines.raw KILL events, dominant side per match (player_match_side MV) |
| 16 | Achievements engine + badge | ✅ done | 24 achievements, 6 tiers; AchievementBadge with tooltip + link to detail page |
| 17 | Comparison view | ✅ done | 1v1 layout, side-by-side stat table, head-to-head, weapons, badges |
| 18 | Records page split (all-time + single-game) | ✅ done | both pages with filters + expand |
| 19 | Country flag rendering | ✅ done | switched to flagcdn.com PNG (Windows didn't render emoji) |

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

### 2026-05-12 — HLL-Records parity (B1+B2+B3): playtime%, win/map, top weapon, per-class, with/against, melee

Post-Roadmap pass closing visible gaps vs hllrecords.com layout.

| Commit | Phase | Scope |
|---|---|---|
| `39d1b04e` | B1 | recent_matches.time_pct, top_maps.win_pct, best_single_game.top_weapon |
| `2554bddb` | B1-fix + B2 | ROUND-numeric-cast fix, /api/best-single-game-by-class endpoint, 9 per-class cards on RecordsSingleGame |
| `f7ae789c` | B3 | played_with_against (teammates+opponents from MV self-join), melee_meta (last melee death + current streak) |

Real prod numbers worth keeping:
- Best single-match melee record: [86] UA Melitopol — 79 kills with M3 KNIFE on mortain_warfare_day.
- Пакет с пакетами top teammate Шихта (183 matches) is also top opponent Шихта (118 matches) — typical of a clan core rotating sides.

Combat Effectiveness metric considered, declined: vague spec, mostly redundant with existing `sort=combat` and `sort=kpm` on the leaderboard.

### 2026-05-12 — Roadmap COMPLETE: P0+P1+P2+P3+P4 all deployed

Full sequence of commits since the post-Phase-5 Roadmap was written:

| Commit | Phase | Scope |
|---|---|---|
| `23ea6a81` | P0#1 | Country flag → flagcdn.com PNG (Windows fix) |
| `f609c110` | P0#2,#3 | Achievement descriptions visible + MV refresh thread |
| `346277bf` | P1 | Multi-player compare via localStorage, /compare/:ids |
| `50942260` | P2a | First seen, mode/faction pref, top maps, alt names |
| `0d090488` | P2b1 | Kill/death by class + melee callout + top servers |
| `48f46da1` | P2b2 | Win rate per side (Allies/Axis) |
| `84b8e444` | P2c | Recharts radar + progression sparkline |
| `977fc617` | P3 | Faction split filter (US/GB/USSR/Wehrmacht/DAK) |
| `623f7913` | P4a | Nemesis stamp + Loved/Hated map + Playstyle card |
| `df5fb20e` | P4b | Hall of Shame page + deaths_by_tk sort |
| `3d08e2f8` | P4c | Time-of-day heatmap + match titles + 4 hidden achievements |

Production sanity checks done after each deploy. Real samples:

- Side filter Axis (top kills): 287ms via player_match_side MV join.
- Head-to-head: Пакет с пакетами 112 vs BaNnY 308 (FG42 x4 most used).
- Faction USSR: 2 qualifying players over min_matches=50 (small slice
  because Eastern Front has narrower coverage in the MV).
- Win rate: BaNnY 59.9% overall, Axis 63.1% > Allies 57.1%.
- Hour distribution: prime time 18-22 for active players.
- Achievement pool: 24 → 28 (4 new hidden tier rare/epic).
- Hall of Shame top "Незграби": Heartattack333 (194), ᛋᛏᚨᛋ (159).

### 2026-05-12 — Roadmap P0/P1: country flag + ach descriptions + MV cron + multi-compare

- **P0 #1 country flag** (commit `23ea6a81`): switched from Unicode RIS letters
  to flagcdn.com PNG `24x18` + `48x36` srcSet. Windows browsers now render.
- **P0 #2 achievement descriptions** (commit `f609c110`): added 6th tuple
  element to `ACHIEVEMENTS` in achievements.py; `description` field flows
  through `/api/achievements` → `AchievementStat` → AchievementsPage card
  subtitle + AchievementDetailPage prominent header line. Removed local
  `ACH_DESCRIPTIONS` map in AchievementBadge.tsx — single source of truth.
- **P0 #3 MV refresh thread** (commit `f609c110`): background daemon thread
  in main.py calls `REFRESH MATERIALIZED VIEW CONCURRENTLY player_match_side`
  every `MV_REFRESH_INTERVAL_SECONDS` (default 3600). Errors logged, swallowed.
  No new infra/deps.
- **P1 multi-player compare** (commit `<next>`): localStorage compare list
  via `useCompareList` hook (max 4 players). Floating `<CompareBar>` always
  visible when list ≥ 1. ComparePage route changed from `/compare/:id1/:id2`
  to `/compare/:ids` (comma-separated). Renders rich 1v1 layout for N=2,
  compact table for N=3..4 (no head-to-head — would be too noisy with N*N
  pairs). `<AddToCompareButton>` on PlayerDetailPage replaces prompt-based
  ⚖ button with toggle.

### 2026-05-12 — Phase 5: side filter + Compare enrichment + Records bug fix

- **Materialized view `player_match_side`**: derives each player's dominant
  side per match from `log_lines.raw` KILL events via regex
  `'KILL: [^(]+\(([^/]+)/'`. 55968 rows on prod, 11s creation, ~30-60s
  CONCURRENT refresh expected. Side filter query (top-50 Axis) — 287ms via
  index seq scans + bitmap join.
- **Caveat**: log_lines coverage is patchy — matches predating log capture
  have no MV rows. When side filter is active those matches silently drop
  from the result. UI shows tooltip explaining this.
- **Recent matches filter**: hide matches where `kills=0 ∧ deaths≤1`
  (spectator/disconnect noise).
- **Head-to-head**: index-driven query on `log_lines (player1_steamid,
  player2_steamid)`. 92ms for top-2 prolific players (420 mutual kills).
  Real numbers: Пакет с пакетами vs BaNnY → 112 vs 308 kills, top weapons
  GEWEHR 43 vs FG42 x4. "BaNnY домінує (+196)".
- **Compare enrichment**: added head-to-head card, top-3 weapons row,
  full achievement badges (not just count), longest_life_secs row, TK
  death row.
- **Country flag bug fix**: switched from Unicode Regional Indicator Symbol
  Letters to flagcdn.com PNG `https://flagcdn.com/24x18/{iso}.png` because
  Windows browsers ship no flag emoji font.
- **Commits**: `a8df0610` Phase A, `9688f0ab` Phase B, `<next>` country flag.

### 2026-05-12 — Phase 4: match links + flags + clickable PVP + Records split + Achievements + Comparison

- `best_single_game` SELECT was missing `m.id` → `RecordsSingleGamePage`
  had `(r as any).match_id ?? ''` producing broken `/games/` URLs.
  Fixed: added `m.id AS match_id` + `match_id: number` in `SingleGameRow`.
- New endpoints: `/api/player-by-name`, `/api/achievements`,
  `/api/achievements/{id}/players`.
- New pages: AchievementsPage (rarity-sorted grid), AchievementDetailPage
  (paginated holders), ComparePage (1v1).
- AchievementBadge now clickable, with description tooltip from
  ACH_DESCRIPTIONS map mirroring `achievements.py` predicates.
- `<CountryFlag>` component added to HomePage + PlayerDetailPage header.
- Recent matches map_name now links to CRCON public stats
  `http://95.111.230.75:7010/games/{match_id}`.
- PVP victim/killer names clickable → resolve via `findPlayerByName` →
  navigate to `/player/{steam_id}`. Silent no-op when not found.
- Records split into `/records/all-time` + `/records/single-game`.
  `/records` 302 redirects to all-time.
- **Commits**: `8aeb6d5d`, `a90ef261`.

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
