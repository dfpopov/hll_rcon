"""stats_app FastAPI entrypoint.

Mounts CORS, slowapi rate limiting, health probe, top-players leaderboard
with sort/order/pagination + period/weapon/map/min_matches filters, and
dropdown-feeder endpoints /api/maps and /api/weapons.
Player detail page arrives in Phase 3 (Task #9).
"""
import logging
import os
import threading
import time
from typing import Optional
from fastapi import FastAPI, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from db import get_db, SessionLocal
import queries

logger = logging.getLogger(__name__)

# How often to REFRESH the player_match_side materialized view so the side
# filter picks up newly-played matches. 1h is plenty — match cadence is
# tens of matches per day at most, and CONCURRENTLY doesn't block reads.
MV_REFRESH_INTERVAL_SECONDS = int(os.getenv("MV_REFRESH_INTERVAL_SECONDS", "3600"))


def _refresh_player_match_side_loop():
    """Background thread: hourly REFRESH MATERIALIZED VIEW CONCURRENTLY.
    Errors are logged and swallowed — next tick retries.
    """
    while True:
        time.sleep(MV_REFRESH_INTERVAL_SECONDS)
        db = None
        try:
            db = SessionLocal()
            db.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY player_match_side"))
            db.commit()
            logger.info("player_match_side: refreshed")
        except Exception as e:
            logger.warning("player_match_side refresh failed: %s", e)
        finally:
            if db is not None:
                try:
                    db.close()
                except Exception:
                    pass

# Rate limiter — in-memory, single-container scope.
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

app = FastAPI(
    title="HLL Stats — All-time",
    version="0.4.0",
    description="Public read-only all-time statistics from CRCON DB",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.on_event("startup")
def _start_background_jobs():
    """Start the MV refresh thread. daemon=True so it dies with the process."""
    t = threading.Thread(target=_refresh_player_match_side_loop, daemon=True)
    t.start()
    logger.info("started player_match_side refresh thread (interval=%ds)", MV_REFRESH_INTERVAL_SECONDS)

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://95.111.230.75:7012,http://localhost:7012,http://localhost:5173",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOWED_ORIGINS if o.strip()],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/health")
@limiter.exempt
def health(request: Request):
    return {"status": "ok", "service": "stats_app", "version": "0.4.0"}


@app.get("/api/top-players")
@limiter.limit("60/minute")
def get_top_players(
    request: Request,
    sort: str = Query(default="kills"),
    order: str = Query(default="desc"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    min_matches: int = Query(default=50, ge=0, le=10000,
                              description="Players with fewer than this number of matches are excluded"),
    period: Optional[str] = Query(default=None, description="7d | 30d | 90d | empty=all"),
    weapon: Optional[str] = Query(default=None, description="filter players who used this weapon at least once"),
    map_name: Optional[str] = Query(default=None, description="filter to specific map"),
    search: Optional[str] = Query(default=None, min_length=2, max_length=64,
                                   description="case-insensitive substring match on player name"),
    game_mode: Optional[str] = Query(default=None, description="warfare | offensive | skirmish"),
    weapon_class: Optional[str] = Query(default=None,
                                         description="Sniper Rifle | Machine Gun | Artillery | ..."),
    side: Optional[str] = Query(default=None, description="Allies | Axis (matches without log coverage are excluded)"),
    db: Session = Depends(get_db),
):
    """Aggregated all-time per-player stats with sort, pagination, filters."""
    if sort not in queries.SORT_COLUMNS:
        return JSONResponse(
            {"detail": f"sort must be one of: {sorted(queries.SORT_COLUMNS.keys())}"},
            status_code=400,
        )
    if period is not None and period not in queries.PERIOD_INTERVALS:
        return JSONResponse(
            {"detail": f"period must be one of: {sorted(queries.PERIOD_INTERVALS.keys())} or empty"},
            status_code=400,
        )
    if game_mode is not None and game_mode.lower() not in queries.GAME_MODES:
        return JSONResponse(
            {"detail": f"game_mode must be one of: {sorted(queries.GAME_MODES.keys())} or empty"},
            status_code=400,
        )
    if side is not None and side not in queries.SIDES_OR_FACTIONS:
        return JSONResponse(
            {"detail": f"side must be one of: {sorted(queries.SIDES_OR_FACTIONS)} or empty"},
            status_code=400,
        )

    rows = queries.top_players(
        db,
        sort=sort, order=order, limit=limit, offset=offset,
        min_matches=min_matches, period=period, weapon=weapon,
        map_name=map_name, search=search, game_mode=game_mode, weapon_class=weapon_class,
        side=side,
    )
    total = queries.top_players_count(
        db,
        min_matches=min_matches, period=period, weapon=weapon,
        map_name=map_name, search=search, game_mode=game_mode, weapon_class=weapon_class,
        side=side,
    )
    return {
        "count": len(rows),
        "total": total,
        "limit": limit,
        "offset": offset,
        "sort": sort,
        "order": order,
        "min_matches": min_matches,
        "period": period,
        "weapon": weapon,
        "map_name": map_name,
        "search": search,
        "game_mode": game_mode,
        "weapon_class": weapon_class,
        "side": side,
        "results": rows,
    }


@app.get("/api/weapon-classes")
@limiter.limit("60/minute")
def get_weapon_classes(request: Request, db: Session = Depends(get_db)):
    """List of weapon classes with their example weapons and counts."""
    return {"classes": queries.get_weapon_classes_with_examples(db)}


@app.get("/api/best-single-game")
@limiter.limit("60/minute")
def get_best_single_game(
    request: Request,
    metric: str = Query(default="kills"),
    limit: int = Query(default=20, ge=1, le=100),
    side: Optional[str] = Query(default=None, description="Allies | Axis"),
    db: Session = Depends(get_db),
):
    """Single-match records: best `metric` in any single game ever played."""
    if metric not in queries.SINGLE_GAME_METRICS:
        return JSONResponse(
            {"detail": f"metric must be one of: {sorted(queries.SINGLE_GAME_METRICS.keys())}"},
            status_code=400,
        )
    if side is not None and side not in queries.SIDES_OR_FACTIONS:
        return JSONResponse(
            {"detail": f"side must be one of: {sorted(queries.SIDES_OR_FACTIONS)} or empty"},
            status_code=400,
        )
    rows = queries.best_single_game(db, metric=metric, limit=limit, side=side)
    return {"metric": metric, "count": len(rows), "side": side, "results": rows}


@app.get("/api/player/{steam_id}")
@limiter.limit("60/minute")
def get_player_detail(
    request: Request,
    steam_id: str,
    db: Session = Depends(get_db),
):
    """Full per-player detail: profile + top weapons + PVP + recent matches."""
    result = queries.player_detail(db, steam_id)
    if not result:
        return JSONResponse({"detail": "player not found"}, status_code=404)
    return result


@app.get("/api/head-to-head")
@limiter.limit("60/minute")
def get_head_to_head(
    request: Request,
    p1: str = Query(min_length=1),
    p2: str = Query(min_length=1),
    db: Session = Depends(get_db),
):
    """Direct PvP record between two players — kill counts in each direction
    plus the top weapon used. Both p1/p2 are steam_id_64 strings."""
    if p1 == p2:
        return JSONResponse({"detail": "p1 and p2 must differ"}, status_code=400)
    return queries.head_to_head(db, p1, p2)


@app.get("/api/player-by-name")
@limiter.limit("60/minute")
def get_player_by_name(
    request: Request,
    name: str = Query(min_length=1, max_length=100),
    db: Session = Depends(get_db),
):
    """Lookup steam_id by player name (used to make PVP names clickable)."""
    sid = queries.find_player_by_name(db, name)
    if not sid:
        return JSONResponse({"detail": "player not found"}, status_code=404)
    return {"steam_id": sid, "name": name}


@app.get("/api/achievements")
@limiter.limit("30/minute")  # heavier query — lower limit
def get_achievements_stats(request: Request, db: Session = Depends(get_db)):
    """List all achievements with stats: earned_count + percentage of players."""
    return {"achievements": queries.compute_achievement_stats(db)}


@app.get("/api/achievements/{achievement_id}/players")
@limiter.limit("30/minute")
def get_players_with_achievement(
    request: Request,
    achievement_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """List players who earned a specific achievement, paginated."""
    return queries.players_with_achievement(db, achievement_id, limit, offset)


@app.get("/api/maps")
@limiter.limit("60/minute")
def get_maps(request: Request, db: Session = Depends(get_db)):
    """List of distinct map_name values for dropdown."""
    return {"maps": queries.get_unique_maps(db)}


@app.get("/api/weapons")
@limiter.limit("60/minute")
def get_weapons(request: Request, db: Session = Depends(get_db)):
    """List of all weapon names used at least once."""
    return {"weapons": queries.get_unique_weapons(db)}
