"""stats_app FastAPI entrypoint.

Mounts CORS, health probe, and Phase-1 top-kills endpoint. Filters arrive
in Phase 2 (see PLAN.md).
"""
import os
from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from db import get_db
import queries

app = FastAPI(
    title="HLL Stats — All-time",
    version="0.1.0",
    description="Public read-only all-time statistics from CRCON DB",
)

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
def health():
    return {"status": "ok", "service": "stats_app", "version": "0.1.0"}


@app.get("/api/top-kills")
def get_top_kills(
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Top players by total kills across all matches.

    Phase 1: no filters. Phase 2 adds period/weapon/map/side params.
    """
    rows = queries.top_kills(db, limit=limit)
    return {"count": len(rows), "results": rows}
