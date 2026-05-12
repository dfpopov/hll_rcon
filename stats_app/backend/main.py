"""stats_app FastAPI entrypoint.

Mounts CORS, slowapi rate limiting, health probe, and the unified
/api/top-players endpoint with sort/order/pagination support.
Per-resource filters (period/weapon/map/side) and player detail
arrive in subsequent phases — see PLAN.md.
"""
import os
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
# 60 req/min/IP is generous for browsers polling a leaderboard.
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

app = FastAPI(
    title="HLL Stats — All-time",
    version="0.2.0",
    description="Public read-only all-time statistics from CRCON DB",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — restrictive: only the public host. Extend when Cloudflare DNS is added.
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
    return {"status": "ok", "service": "stats_app", "version": "0.2.0"}


@app.get("/api/top-players")
@limiter.limit("60/minute")
def get_top_players(
    request: Request,
    sort: str = Query(default="kills", description="kills|deaths|teamkills|kd_ratio|kpm|playtime|matches|level"),
    order: str = Query(default="desc", description="desc|asc"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """Aggregated all-time per-player stats with sort and pagination.

    Filters (period/weapon/map/side) arrive in Phase 2 — see Task #8.
    """
    if sort not in queries.SORT_COLUMNS:
        return JSONResponse(
            {"detail": f"sort must be one of: {sorted(queries.SORT_COLUMNS.keys())}"},
            status_code=400,
        )
    rows = queries.top_players(db, sort=sort, order=order, limit=limit, offset=offset)
    total = queries.top_players_count(db)
    return {
        "count": len(rows),
        "total": total,
        "limit": limit,
        "offset": offset,
        "sort": sort,
        "order": order,
        "results": rows,
    }
