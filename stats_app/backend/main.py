"""stats_app FastAPI entrypoint.

Mounts CORS, slowapi rate limiting, health probe, top-players leaderboard
with sort/order/pagination + period/weapon/map/min_matches filters, and
dropdown-feeder endpoints /api/maps and /api/weapons.
Player detail page arrives in Phase 3 (Task #9).
"""
import os
from typing import Optional
from fastapi import FastAPI, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from db import get_db
import queries

# Rate limiter — in-memory, single-container scope.
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

app = FastAPI(
    title="HLL Stats — All-time",
    version="0.3.0",
    description="Public read-only all-time statistics from CRCON DB",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
    return {"status": "ok", "service": "stats_app", "version": "0.3.0"}


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

    rows = queries.top_players(
        db,
        sort=sort, order=order, limit=limit, offset=offset,
        min_matches=min_matches, period=period, weapon=weapon,
        map_name=map_name, search=search,
    )
    total = queries.top_players_count(
        db,
        min_matches=min_matches, period=period, weapon=weapon,
        map_name=map_name, search=search,
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
        "results": rows,
    }


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
