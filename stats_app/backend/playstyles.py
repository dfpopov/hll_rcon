"""Playstyle classification.

Declarative archetype list keyed off the aggregate player profile from
queries._all_player_profiles. The first matching predicate wins, so order
runs most-specific → least-specific. A Універсал default catches the rest.

Single source of truth — used by:
- player_detail to label one player
- /api/playstyles + /api/playstyles/{id}/players for the server-wide page

A small TTL cache (1h) avoids classifying 28k players on every request.
"""
from typing import Any, Callable, Dict, List, Optional
import time


def _compute_ctx(p: Dict[str, Any]) -> Dict[str, float]:
    """Derive ratios + KPM for predicate evaluation. Idempotent + safe on
    None / missing fields."""
    combat  = p.get("combat")  or 0
    offense = p.get("offense") or 0
    defense = p.get("defense") or 0
    support = p.get("support") or 0
    total = combat + offense + defense + support
    minutes = max(1.0, (p.get("total_seconds") or 0) / 60.0)
    kills = p.get("kills") or 0
    return {
        "combat_pct":  combat  / total * 100 if total else 0.0,
        "offense_pct": offense / total * 100 if total else 0.0,
        "defense_pct": defense / total * 100 if total else 0.0,
        "support_pct": support / total * 100 if total else 0.0,
        # KPM derived from totals (not the per-match AVG that profile.kpm holds
        # in player_detail), so it's available in aggregate iteration too.
        "kpm_derived": kills / minutes,
        "tk_rate":     (p.get("teamkills") or 0) / max(1, kills) * 100,
    }


_MIN_MATCHES = 10
# Players below this are excluded from aggregate playstyle stats — single-match
# accounts are noise that overwhelm the Універсал bucket otherwise.
_AGGREGATE_MIN_MATCHES = 10


# (id, title, emoji, color, description, predicate)
# Predicate signature: (profile, ctx) → bool. Order = priority.
PLAYSTYLES: List[Dict[str, Any]] = [
    # ── Very specific signatures first ─────────────────────────────────
    {
        "id": "logistician", "title": "Підтримка", "emoji": "📦", "color": "text-cyan-300",
        "description": "Support 50%+ score — будівник, медик, постачальник або їх комбінація",
        "predicate": lambda p, c: c["support_pct"] >= 50 and (p.get("matches_played") or 0) >= _MIN_MATCHES,
    },
    {
        "id": "kamikadze", "title": "Камікадзе", "emoji": "💣", "color": "text-red-400",
        "description": "TK rate 10%+ при 100+ матчів — небезпечний для своїх",
        "predicate": lambda p, c: c["tk_rate"] >= 10 and (p.get("matches_played") or 0) >= 100,
    },
    {
        "id": "sharpshooter", "title": "Снайпер-вбивця", "emoji": "🎯", "color": "text-amber-300",
        "description": "K/D 2.5+ та серія 30+ в одному матчі",
        "predicate": lambda p, c: (p.get("kd_ratio") or 0) >= 2.5 and (p.get("best_kills_streak") or 0) >= 30,
    },
    {
        "id": "veteran_marksman", "title": "Ветеран-стрілець", "emoji": "🪖", "color": "text-emerald-300",
        "description": "Рівень 200+, K/D 1.5+, 500+ матчів",
        "predicate": lambda p, c: ((p.get("level") or 0) >= 200
                                    and (p.get("kd_ratio") or 0) >= 1.5
                                    and (p.get("matches_played") or 0) >= 500),
    },
    {
        "id": "commander", "title": "Командир", "emoji": "🎖", "color": "text-amber-300",
        "description": "Збалансований: всі 4 score-категорії 20%+ при 200+ матчів",
        "predicate": lambda p, c: ((p.get("matches_played") or 0) >= 200
                                    and c["combat_pct"]  >= 20
                                    and c["offense_pct"] >= 20
                                    and c["defense_pct"] >= 20
                                    and c["support_pct"] >= 20),
    },
    {
        "id": "kpm_killer", "title": "Молотобоєць", "emoji": "🔥", "color": "text-orange-300",
        "description": "KPM 1.5+ при combat 40%+ — нон-стоп вбивства",
        "predicate": lambda p, c: (c["kpm_derived"] >= 1.5 and c["combat_pct"] >= 40
                                    and (p.get("matches_played") or 0) >= _MIN_MATCHES),
    },
    {
        "id": "survivor_master", "title": "Майстер жити", "emoji": "🛡", "color": "text-cyan-300",
        "description": "Найдовше життя — 20+ хвилин без смерті",
        "predicate": lambda p, c: ((p.get("longest_life_secs") or 0) >= 1200
                                    and (p.get("matches_played") or 0) >= _MIN_MATCHES),
    },
    {
        "id": "zerg", "title": "Зерг", "emoji": "🐝", "color": "text-amber-400",
        "description": "5000+ kills при K/D < 1.0 — кількість понад якість",
        "predicate": lambda p, c: (p.get("kills") or 0) >= 5000 and (p.get("kd_ratio") or 0) < 1.0,
    },
    {
        "id": "glider", "title": "Глайдер", "emoji": "🪂", "color": "text-sky-300",
        "description": "10+ хв життя без активності, K/D <1.5",
        "predicate": lambda p, c: ((p.get("longest_life_secs") or 0) >= 600
                                    and (p.get("kd_ratio") or 0) < 1.5
                                    and (p.get("matches_played") or 0) >= _MIN_MATCHES),
    },
    {
        "id": "lone_wolf", "title": "Соло-вовк", "emoji": "🐺", "color": "text-zinc-300",
        "description": "Support менше 10% при 200+ матчів — все сам",
        "predicate": lambda p, c: (p.get("matches_played") or 0) >= 200 and c["support_pct"] < 10,
    },

    # ── K/D-extreme catchers BEFORE generic geometric splits ──────────
    # Otherwise low-K/D players hit Стіна/Штурмовик based on score ratios
    # and the K/D-based archetypes never fire.
    {
        "id": "runner", "title": "Тікач", "emoji": "🏃", "color": "text-zinc-400",
        "description": "Deaths удвічі більше за kills — постійний клієнт респауну",
        "predicate": lambda p, c: ((p.get("deaths") or 0) > (p.get("kills") or 0) * 2
                                    and (p.get("matches_played") or 0) >= _MIN_MATCHES),
    },
    {
        "id": "sacrificial", "title": "Жертовний", "emoji": "💀", "color": "text-rose-300",
        "description": "K/D менше 0.8 — кидається в саме пекло",
        "predicate": lambda p, c: (p.get("kd_ratio") or 0) < 0.8 and (p.get("matches_played") or 0) >= _MIN_MATCHES,
    },

    # ── Combat-heavy archetypes ────────────────────────────────────────
    {
        "id": "trench_defender", "title": "Захисник окопу", "emoji": "🏰", "color": "text-emerald-300",
        "description": "Combat 50%+ з ухилом у захист (10+ матчів)",
        "predicate": lambda p, c: (c["combat_pct"] >= 50 and c["defense_pct"] > c["offense_pct"]
                                    and (p.get("matches_played") or 0) >= _MIN_MATCHES),
    },
    {
        "id": "combat_reaper", "title": "Бойовий жнець", "emoji": "⚔️", "color": "text-red-300",
        "description": "Combat 50%+ з ухилом в атаку (10+ матчів)",
        "predicate": lambda p, c: c["combat_pct"] >= 50 and (p.get("matches_played") or 0) >= _MIN_MATCHES,
    },

    # ── Generic geometric splits (now gated so they don't catch newbies) ──
    {
        "id": "wall", "title": "Стіна", "emoji": "🛡", "color": "text-blue-300",
        "description": "Defense значно більше за offense — тримає точку (10+ матчів)",
        "predicate": lambda p, c: (c["defense_pct"] > c["offense_pct"] + 15
                                    and (p.get("matches_played") or 0) >= _MIN_MATCHES),
    },
    {
        "id": "assault", "title": "Штурмовик", "emoji": "🗡", "color": "text-orange-300",
        "description": "Offense значно більше за defense — перший на точці (10+ матчів)",
        "predicate": lambda p, c: (c["offense_pct"] > c["defense_pct"] + 15
                                    and (p.get("matches_played") or 0) >= _MIN_MATCHES),
    },
    {
        "id": "sharp_versatile", "title": "Влучний універсал", "emoji": "🦅", "color": "text-amber-300",
        "description": "K/D 2.0+ зі збалансованими score-категоріями",
        "predicate": lambda p, c: ((p.get("kd_ratio") or 0) >= 2.0
                                    and (p.get("matches_played") or 0) >= _MIN_MATCHES),
    },

    # ── Default catcher ────────────────────────────────────────────────
    {
        "id": "versatile", "title": "Універсал", "emoji": "🛡", "color": "text-zinc-300",
        "description": "Збалансований стиль або замало даних",
        "predicate": lambda p, c: True,
    },
]


def classify_one(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Return the first matching playstyle metadata for a single profile."""
    ctx = _compute_ctx(profile)
    for ps in PLAYSTYLES:
        try:
            if ps["predicate"](profile, ctx):
                return {
                    "id": ps["id"], "title": ps["title"], "emoji": ps["emoji"],
                    "color": ps["color"], "description": ps["description"],
                }
        except (TypeError, ValueError, ZeroDivisionError):
            continue
    # Fallback (shouldn't be reachable because versatile is always True)
    return {"id": "versatile", "title": "Універсал", "emoji": "🛡",
            "color": "text-zinc-300", "description": ""}


# In-process TTL cache for the aggregate distribution. Iterating 28k+
# profiles to classify is fast but not per-request fast (~1-2s on prod);
# 1h TTL is plenty since playstyles don't shift fast.
_AGGREGATE_TTL_SECONDS = 3600
_aggregate_cache: Dict[str, Any] = {"computed_at": 0.0, "buckets": None}


def compute_playstyle_stats(profiles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Bucket all profiles by their playstyle, return ordered metadata
    list with player_count + sample top-5 by kills per bucket. Profiles
    below _AGGREGATE_MIN_MATCHES are skipped — single-match noise should
    not overwhelm the catch-all bucket.
    """
    buckets: Dict[str, List[Dict[str, Any]]] = {ps["id"]: [] for ps in PLAYSTYLES}
    for p in profiles:
        if (p.get("matches_played") or 0) < _AGGREGATE_MIN_MATCHES:
            continue
        ctx = _compute_ctx(p)
        for ps in PLAYSTYLES:
            try:
                if ps["predicate"](p, ctx):
                    buckets[ps["id"]].append(p)
                    break
            except (TypeError, ValueError, ZeroDivisionError):
                continue
    result = []
    for ps in PLAYSTYLES:
        bucket = buckets[ps["id"]]
        samples = sorted(bucket, key=lambda x: (x.get("kills") or 0), reverse=True)[:5]
        result.append({
            "id": ps["id"],
            "title": ps["title"],
            "emoji": ps["emoji"],
            "color": ps["color"],
            "description": ps["description"],
            "player_count": len(bucket),
            "sample_players": [
                {
                    "steam_id": x["steam_id"],
                    "name": x.get("name"),
                    "avatar_url": x.get("avatar_url"),
                    "kills": int(x.get("kills") or 0),
                    "matches_played": int(x.get("matches_played") or 0),
                }
                for x in samples
            ],
        })
    return result


def get_cached_stats_or_compute(profiles_fn: Callable[[], List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Return cached aggregate stats, refreshing if older than TTL."""
    now = time.time()
    if (_aggregate_cache["buckets"] is not None
            and now - _aggregate_cache["computed_at"] < _AGGREGATE_TTL_SECONDS):
        return _aggregate_cache["buckets"]
    fresh = compute_playstyle_stats(profiles_fn())
    _aggregate_cache["computed_at"] = now
    _aggregate_cache["buckets"] = fresh
    return fresh


def players_with_playstyle(
    profiles: List[Dict[str, Any]],
    playstyle_id: str,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """List all players matching a specific playstyle. Sorted by kills desc.
    Same iteration shape as compute_playstyle_stats — share underlying buckets
    in callers if you want one pass.
    """
    bucket: List[Dict[str, Any]] = []
    target_ps: Optional[Dict[str, Any]] = next((ps for ps in PLAYSTYLES if ps["id"] == playstyle_id), None)
    if target_ps is None:
        return {"count": 0, "total": 0, "limit": limit, "offset": offset, "results": []}
    for p in profiles:
        if (p.get("matches_played") or 0) < _AGGREGATE_MIN_MATCHES:
            continue
        ctx = _compute_ctx(p)
        for ps in PLAYSTYLES:
            try:
                if ps["predicate"](p, ctx):
                    if ps["id"] == playstyle_id:
                        bucket.append(p)
                    break
            except (TypeError, ValueError, ZeroDivisionError):
                continue
    bucket.sort(key=lambda x: (x.get("kills") or 0), reverse=True)
    paged = bucket[offset:offset + limit]
    return {
        "count": len(paged),
        "total": len(bucket),
        "limit": limit,
        "offset": offset,
        "playstyle": {
            "id": target_ps["id"], "title": target_ps["title"], "emoji": target_ps["emoji"],
            "color": target_ps["color"], "description": target_ps["description"],
        },
        "results": paged,
    }
