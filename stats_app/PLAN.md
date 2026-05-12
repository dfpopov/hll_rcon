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

---

## Roadmap (post-Phase-5)

Ordered by priority. Each item is sized at least 1 commit. PROGRESS.md
tracks status; this section is the queue.

### P0 — small fixes / clarifications (ship first)

1. **Country flag rendering on Windows** — switch `<CountryFlag>` from
   Unicode RIS letters to `flagcdn.com` PNG. Ships with this commit.
2. **Achievement requirements visibility** — current tooltip on the badge
   isn't enough. Make description prominent in three places:
   - `/achievements` card: subtitle line under the title
   - `/achievements/{id}` header: large description paragraph
   - `<AchievementBadge>` tooltip: ensure all 24 ach IDs have descriptions
     (some may be missing).
3. **MV refresh cron** — hourly `REFRESH MATERIALIZED VIEW CONCURRENTLY
   player_match_side` so new matches enter the side filter without manual
   migration re-run. Implementation: add a service to `compose.yaml` that
   runs `crond` with a single entry, or a host-side `crontab -e`. Prefer
   container so it ships with the repo.

### P1 — feature: multi-player comparison

4. **"Додати до порівняння" + localStorage** — up to 4 players in a
   compare set. On `PlayerDetailPage`, add a button next to the existing
   ⚖ Порівняти. Persist as `localStorage.compareList = [{steam_id, name,
   added_at}]`. Floating compare-bar at bottom of screen shows current
   chips + "Порівняти (N)" CTA → `/compare?ids=sid1,sid2,sid3,sid4`.
   - 1v1: existing rich layout (head-to-head + weapons + achievements + stat table)
   - 1v3 or 1v4: simpler compact table — show only the headline columns
     (level/kills/K-D/KPM/matches/hours/win-rate) + achievements badges
     (small), drop head-to-head (would be N*N pairs, too noisy).

### P2 — PlayerDetailPage upgrades (HLL Records-inspired)

Screenshots from `hllrecords.com/hilf` showed several useful sections. Map
them to our data:

5. **Faction preference badge** — % time on Allies vs Axis from `player_match_side` MV. Show on profile header next to country.
6. **First seen date** — `MIN(m.start)` per player. Trivial.
7. **Game mode preference** — % warfare / offensive / skirmish from `map_name` pattern. Trivial.
8. **Most played maps** (top 10 with match counts) — `COUNT(*) GROUP BY map_name LIMIT 10`. Trivial.
9. **100+ kill matches counter** — `COUNT(*) WHERE kills >= 100`. Trivial.
10. **Kill type breakdown** (Infantry / MG / Sniper / Armor / Artillery /
    Explosive / Unknown) — classify each weapon in `weapons` jsonb, aggregate.
    Visualized as a horizontal stacked bar + tooltip with absolute counts.
    Re-uses existing `weapon_classes.py` classifier.
11. **Melee section** — sum kills/deaths where weapon ∈ `{FELDSPATEN,
    KNIFE, M3 KNIFE, BAYONET}` (and similar melee tags). Need a small
    melee weapon list.
12. **Win rate** — needs join `map_history.result` jsonb + side from MV.
    "60% as Allies, 45% as Axis." Medium effort, needs query.
13. **Most played servers** — `player_sessions` has `server_name`. JOIN
    not currently used. Adds a small server list to the profile.
14. **Alt names** — collect `MAX(persona_name)` + `DISTINCT ps.name` for
    the same `playersteamid_id`. Show as chips.
15. **Radar chart** (KPM / KDR / Combat / Support / Offense / Defense
    normalized vs server median) — needs Recharts/Chart.js. Medium.
16. **Progression chart** (rolling 20-match avg of selected metric) —
    same chart lib. Show tabs: Win rate / KPM / KD / Combat / Support / etc.

### P3 — side filter Phase 2

17. **Faction split** (US / GB / USSR / Wehrmacht / DAK) — add `theater`
    lookup table by `map_name`: Western (US/Wehrmacht), Eastern
    (USSR/Wehrmacht), Africa (GB/DAK). UI: extend side select from 2 to
    5+ options. Same MV under the hood, just an additional map join.

### P4 — fun / meme stats (earlier brainstorm)

18. **Nemesis stamp** — big highlight card on profile showing top-1
    `killed_by` entry as the player's eternal rival.
19. **Loved/Hated map** — best & worst K/D map.
20. **Playstyle classifier** — derive Camper / Rambo / Medic Saint / Tank
    Crusher etc. from combat/offense/defense/support ratios.
21. **Hall of Shame** — anti-records page: most TKs, most deaths_by_tk,
    worst K/D single game.
22. **Time-of-day heatmap** — GitHub-style activity calendar from
    `m.start` per match the player played.
23. **Match titles** — auto-generated headline for outstanding matches
    ("Сталінградська різанина" on 80+ kills, "Розстріл своїми" on 50+
    deaths_by_tk).
24. **Hidden achievements** — easter eggs with absurd triggers ("Дзеркало"
    = exact K=D ≥ 50 in one match, etc.).
