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


_MIN_MATCHES = 5
# Players below this are excluded from aggregate playstyle stats — single-match
# accounts are noise that overwhelm the Універсал bucket otherwise.
_AGGREGATE_MIN_MATCHES = 5


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
        "id": "zerg", "title": "Зерг", "emoji": "🐝", "color": "text-amber-400",
        "description": "3000+ kills при K/D < 1.0 — кількість понад якість",
        "predicate": lambda p, c: (p.get("kills") or 0) >= 3000 and (p.get("kd_ratio") or 0) < 1.0,
    },
    {
        "id": "lone_wolf", "title": "Соло-вовк", "emoji": "🐺", "color": "text-zinc-300",
        "description": "Support менше 10% при 200+ матчів — все сам",
        "predicate": lambda p, c: (p.get("matches_played") or 0) >= 200 and c["support_pct"] < 10,
    },

    # ── Weapon-class specialists (need top_kill_class enrichment) ──────
    {
        "id": "knife_master", "title": "Майстер ножа", "emoji": "🔪", "color": "text-rose-300",
        "description": "Топ зброя — ближній бій (Melee), 10+ melee-вбивств",
        "predicate": lambda p, c: (p.get("top_kill_class") == "Melee"
                                    and (p.get("top_kill_class_kills") or 0) >= 10),
    },
    {
        "id": "artilleryman", "title": "Артилерист", "emoji": "💥", "color": "text-yellow-300",
        "description": "Топ зброя — артилерія, 20%+ усіх вбивств",
        "predicate": lambda p, c: (p.get("top_kill_class") == "Artillery"
                                    and (p.get("top_kill_class_pct") or 0) >= 20),
    },
    {
        "id": "pure_sniper", "title": "Чистий снайпер", "emoji": "🎯", "color": "text-sky-300",
        "description": "Топ зброя — снайперська гвинтівка, 25%+ усіх вбивств",
        "predicate": lambda p, c: (p.get("top_kill_class") == "Sniper Rifle"
                                    and (p.get("top_kill_class_pct") or 0) >= 25),
    },
    {
        "id": "tanker", "title": "Танкіст", "emoji": "🚜", "color": "text-orange-300",
        "description": "Топ зброя — танкова гармата або AT, 20%+ усіх вбивств",
        "predicate": lambda p, c: (p.get("top_kill_class") in ("Tank Gun", "Anti-Tank")
                                    and (p.get("top_kill_class_pct") or 0) >= 20),
    },
    {
        "id": "night_owl", "title": "Нічна сова", "emoji": "🌚", "color": "text-indigo-300",
        "description": "Пік активності о 0:00-5:59 — нічні гравці",
        "predicate": lambda p, c: ((p.get("peak_hour") if p.get("peak_hour") is not None else -1) in (0, 1, 2, 3, 4, 5)
                                    and (p.get("matches_played") or 0) >= _MIN_MATCHES),
    },
    {
        "id": "ritual", "title": "Ритуал", "emoji": "⏰", "color": "text-violet-200",
        "description": "60%+ матчів в одну й ту саму годину — людина-розклад",
        "predicate": lambda p, c: ((p.get("peak_hour_pct") or 0) >= 60
                                    and (p.get("matches_played") or 0) >= 50),
    },

    # ── Curiosity archetypes — must come BEFORE the generic K/D / ratio
    # catchers so their specific combos win priority. Otherwise a level-200
    # K/D 0.7 player would hit Жертовний instead of more interesting Кістка.
    {
        "id": "kpm_wizard", "title": "Чарівник KPM", "emoji": "🧙", "color": "text-violet-300",
        "description": "KPM 1.0+ при combat <30% — вбиває не combat-зброєю (тенки, артилерія, гранати)",
        "predicate": lambda p, c: (c["kpm_derived"] >= 1.0 and c["combat_pct"] < 30
                                    and (p.get("matches_played") or 0) >= _MIN_MATCHES),
    },
    {
        "id": "bone", "title": "Кістка", "emoji": "🦴", "color": "text-zinc-400",
        "description": "Високий рівень (150+), низький K/D (<1.0) — гриндив рівень, не стрільбу",
        "predicate": lambda p, c: ((p.get("level") or 0) >= 150
                                    and (p.get("kd_ratio") or 0) < 1.0
                                    and (p.get("matches_played") or 0) >= 100),
    },
    {
        "id": "diamond_in_rough", "title": "Алмаз у грязі", "emoji": "💎", "color": "text-cyan-200",
        "description": "K/D 2.0+ при рівні <50 — талант без часу",
        "predicate": lambda p, c: ((p.get("kd_ratio") or 0) >= 2.0
                                    and (p.get("level") or 0) < 50
                                    and (p.get("matches_played") or 0) >= 20),
    },
    {
        "id": "lottery", "title": "Лотерея", "emoji": "🎰", "color": "text-amber-200",
        "description": "Серія 40+ в одному матчі, але K/D <1.5 — один великий день",
        "predicate": lambda p, c: ((p.get("best_kills_streak") or 0) >= 40
                                    and (p.get("kd_ratio") or 0) < 1.5),
    },
    {
        "id": "master", "title": "Майстер", "emoji": "🥋", "color": "text-amber-400",
        "description": "Рівень 200+, K/D 1.8+, 300+ матчів — справжній гуру",
        "predicate": lambda p, c: ((p.get("level") or 0) >= 200
                                    and (p.get("kd_ratio") or 0) >= 1.8
                                    and (p.get("matches_played") or 0) >= 300),
    },
    {
        "id": "speedster", "title": "Швидкохід", "emoji": "🚀", "color": "text-orange-200",
        "description": "KPM 1.0+ при <50 годин на сервері — ефективний з першої секунди",
        "predicate": lambda p, c: (c["kpm_derived"] >= 1.0
                                    and (p.get("total_seconds") or 0) < 50 * 3600
                                    and (p.get("matches_played") or 0) >= _MIN_MATCHES),
    },
    {
        "id": "slowmo", "title": "Повільник", "emoji": "🦥", "color": "text-zinc-400",
        "description": "KPM <0.3 при 100+ матчів — нікуди не поспішає",
        "predicate": lambda p, c: (c["kpm_derived"] < 0.3
                                    and (p.get("matches_played") or 0) >= 100),
    },
    {
        "id": "tk_martyr", "title": "Мученик ТК", "emoji": "🛐", "color": "text-rose-200",
        "description": "50+ смертей від ТК своїх — магніт для союзницьких куль",
        "predicate": lambda p, c: (p.get("deaths_by_tk") or 0) >= 50,
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
        "description": "Combat 50%+ з ухилом у захист (5+ матчів)",
        "predicate": lambda p, c: (c["combat_pct"] >= 50 and c["defense_pct"] > c["offense_pct"]
                                    and (p.get("matches_played") or 0) >= _MIN_MATCHES),
    },
    {
        "id": "combat_reaper", "title": "Бойовий жнець", "emoji": "⚔️", "color": "text-red-300",
        "description": "Combat 50%+ з ухилом в атаку (5+ матчів)",
        "predicate": lambda p, c: c["combat_pct"] >= 50 and (p.get("matches_played") or 0) >= _MIN_MATCHES,
    },

    # ── Generic geometric splits (now gated so they don't catch newbies) ──
    {
        "id": "wall", "title": "Стіна", "emoji": "🛡", "color": "text-blue-300",
        "description": "Defense значно більше за offense — тримає точку (5+ матчів)",
        "predicate": lambda p, c: (c["defense_pct"] > c["offense_pct"] + 15
                                    and (p.get("matches_played") or 0) >= _MIN_MATCHES),
    },
    {
        "id": "assault", "title": "Штурмовик", "emoji": "🗡", "color": "text-orange-300",
        "description": "Offense значно більше за defense — перший на точці (5+ матчів)",
        "predicate": lambda p, c: (c["offense_pct"] > c["defense_pct"] + 15
                                    and (p.get("matches_played") or 0) >= _MIN_MATCHES),
    },
    {
        "id": "sharp_versatile", "title": "Влучний універсал", "emoji": "🦅", "color": "text-amber-300",
        "description": "K/D 2.0+ зі збалансованими score-категоріями",
        "predicate": lambda p, c: ((p.get("kd_ratio") or 0) >= 2.0
                                    and (p.get("matches_played") or 0) >= _MIN_MATCHES),
    },

    # ── Fill-in archetypes for the "normal" middle ─────────────────────
    {
        "id": "active_player", "title": "Активний", "emoji": "✅", "color": "text-emerald-300",
        "description": "50+ матчів, K/D від 1.0 до 2.0 — рівний середняк",
        "predicate": lambda p, c: ((p.get("matches_played") or 0) >= 50
                                    and 1.0 <= (p.get("kd_ratio") or 0) <= 2.0),
    },
    {
        "id": "combat_fly", "title": "Бойова муха", "emoji": "🦟", "color": "text-orange-200",
        "description": "Менш ніж 50 матчів, K/D 1.0+ — швидко вчиться",
        "predicate": lambda p, c: ((p.get("matches_played") or 0) < 50
                                    and (p.get("matches_played") or 0) >= _MIN_MATCHES
                                    and (p.get("kd_ratio") or 0) >= 1.0),
    },
    {
        "id": "explorer", "title": "Дослідник", "emoji": "🧭", "color": "text-sky-200",
        "description": "10-49 матчів — пробує гру",
        "predicate": lambda p, c: (10 <= (p.get("matches_played") or 0) < 50),
    },
    {
        "id": "rookie", "title": "Початківець", "emoji": "🌱", "color": "text-zinc-200",
        "description": "Менш ніж 10 матчів — ще не зрозумів куди стріляти",
        "predicate": lambda p, c: ((p.get("matches_played") or 0) < 10
                                    and (p.get("matches_played") or 0) >= _MIN_MATCHES),
    },

    # ── Long-life patterns — moved to the END so they don't shadow more
    # specific styles. longest_life_secs is per-match peak, so even one good
    # match qualifies — should only fire when nothing else describes the player.
    {
        "id": "glider", "title": "Глайдер", "emoji": "🪂", "color": "text-sky-300",
        "description": "15+ хв життя без активності, K/D <1.0",
        "predicate": lambda p, c: ((p.get("longest_life_secs") or 0) >= 900
                                    and (p.get("kd_ratio") or 0) < 1.0
                                    and (p.get("matches_played") or 0) >= _MIN_MATCHES),
    },
    {
        "id": "survivor_master", "title": "Майстер жити", "emoji": "🛡", "color": "text-cyan-300",
        "description": "Найдовше життя — 30+ хвилин без смерті, 100+ матчів",
        "predicate": lambda p, c: ((p.get("longest_life_secs") or 0) >= 1800
                                    and (p.get("matches_played") or 0) >= 100),
    },

    # ── Default catcher ────────────────────────────────────────────────
    {
        "id": "versatile", "title": "Універсал", "emoji": "🛡", "color": "text-zinc-300",
        "description": "Збалансований стиль або замало даних",
        "predicate": lambda p, c: True,
    },
]


def _ps_meta(ps: Dict[str, Any]) -> Dict[str, Any]:
    """Strip the predicate, keep only the displayable fields."""
    return {
        "id": ps["id"], "title": ps["title"], "emoji": ps["emoji"],
        "color": ps["color"], "description": ps["description"],
    }


def classify_one(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Return primary playstyle + all other matching archetypes.

    Output shape:
      {"primary": {...}, "also": [{...}, ...]}

    The first matching archetype is the primary (preserving the original
    priority order). The `also` list contains every OTHER archetype whose
    predicate also matches, excluding the always-true `versatile` default
    (which would clutter the list).
    """
    ctx = _compute_ctx(profile)
    matched: list = []
    for ps in PLAYSTYLES:
        if ps["id"] == "versatile":
            continue  # always-true; skip from secondary list
        try:
            if ps["predicate"](profile, ctx):
                matched.append(ps)
        except (TypeError, ValueError, ZeroDivisionError):
            continue

    if not matched:
        # Fall through to default
        versatile = next((ps for ps in PLAYSTYLES if ps["id"] == "versatile"), None)
        return {
            "primary": _ps_meta(versatile) if versatile else
                {"id": "versatile", "title": "Універсал", "emoji": "🛡",
                 "color": "text-zinc-300", "description": ""},
            "also": [],
        }

    return {
        "primary": _ps_meta(matched[0]),
        "also":    [_ps_meta(ps) for ps in matched[1:]],
    }


# In-process TTL cache for the aggregate distribution. Iterating 28k+
# profiles to classify is fast but not per-request fast (~1-2s on prod);
# 1h TTL is plenty since playstyles don't shift fast.
_AGGREGATE_TTL_SECONDS = 3600
_aggregate_cache: Dict[str, Any] = {"computed_at": 0.0, "buckets": None}


def compute_playstyle_stats(profiles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Per-archetype counts. player_count = primary matches; total_count =
    primary + also (any match). Sample top-5 by kills uses primary bucket.

    Profiles below _AGGREGATE_MIN_MATCHES skipped — single-match noise.
    """
    primary_buckets: Dict[str, List[Dict[str, Any]]] = {ps["id"]: [] for ps in PLAYSTYLES}
    total_counts: Dict[str, int] = {ps["id"]: 0 for ps in PLAYSTYLES}
    for p in profiles:
        if (p.get("matches_played") or 0) < _AGGREGATE_MIN_MATCHES:
            continue
        ctx = _compute_ctx(p)
        primary_assigned = False
        for ps in PLAYSTYLES:
            # versatile's predicate is always True — counting it as "also"
            # would tag every player, making the metric useless.
            if ps["id"] == "versatile":
                continue
            try:
                if ps["predicate"](p, ctx):
                    total_counts[ps["id"]] += 1
                    if not primary_assigned:
                        primary_buckets[ps["id"]].append(p)
                        primary_assigned = True
            except (TypeError, ValueError, ZeroDivisionError):
                continue
        # If no real archetype matched, assign to versatile as primary.
        if not primary_assigned:
            primary_buckets["versatile"].append(p)
    result = []
    for ps in PLAYSTYLES:
        bucket = primary_buckets[ps["id"]]
        samples = sorted(bucket, key=lambda x: (x.get("kills") or 0), reverse=True)[:5]
        result.append({
            "id": ps["id"],
            "title": ps["title"],
            "emoji": ps["emoji"],
            "color": ps["color"],
            "description": ps["description"],
            "player_count": len(bucket),
            "total_count": total_counts[ps["id"]],
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
    """List all players whose playstyle matches the given id — either as
    PRIMARY (first match) or ALSO (later matches). Marks each result with
    `is_primary` so the UI can distinguish.

    Earlier this function only counted primary, which contradicted the
    "Також підходить" chips on player profiles: a player would see Майстер
    жити as an also-style but the detail page would show 0 players.
    """
    bucket: List[Dict[str, Any]] = []
    target_ps: Optional[Dict[str, Any]] = next((ps for ps in PLAYSTYLES if ps["id"] == playstyle_id), None)
    if target_ps is None:
        return {"count": 0, "total": 0, "limit": limit, "offset": offset, "results": []}
    for p in profiles:
        if (p.get("matches_played") or 0) < _AGGREGATE_MIN_MATCHES:
            continue
        ctx = _compute_ctx(p)
        # Iterate skipping versatile (always-true catch-all) — track which
        # real archetypes match. If none, the player is purely versatile.
        matched_ids: list = []
        for ps in PLAYSTYLES:
            if ps["id"] == "versatile":
                continue
            try:
                if ps["predicate"](p, ctx):
                    matched_ids.append(ps["id"])
            except (TypeError, ValueError, ZeroDivisionError):
                continue

        if playstyle_id == "versatile":
            # Only include players with no real archetype match.
            if not matched_ids:
                bucket.append({**p, "is_primary": True})
        else:
            if playstyle_id in matched_ids:
                is_primary = (matched_ids[0] == playstyle_id)
                bucket.append({**p, "is_primary": is_primary})
    # Sort primary-first, then by kills.
    bucket.sort(key=lambda x: (not x.get("is_primary"), -(x.get("kills") or 0)))
    paged = bucket[offset:offset + limit]
    return {
        "count": len(paged),
        "total": len(bucket),
        "primary_count": sum(1 for x in bucket if x.get("is_primary")),
        "limit": limit,
        "offset": offset,
        "playstyle": {
            "id": target_ps["id"], "title": target_ps["title"], "emoji": target_ps["emoji"],
            "color": target_ps["color"], "description": target_ps["description"],
        },
        "results": paged,
    }
