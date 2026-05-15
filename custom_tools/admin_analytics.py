"""
admin_analytics.py — Інструмент для аналізу динаміки сервера HLL.

Об'єднує 5 окремих аналізів на основі таблиць map_history,
player_sessions і player_stats:

  1. FILL SPEED ─ скільки хвилин від старту матчу (з ≤25 гравців)
                  до досягнення 30/60/90 одночасних. За картою і за днем.

  2. NET FLOW   ─ після зміни карти: скільки гравців пішло + скільки
                  прийшло за перші 30 хв. Δнетто > 0 = карта тримає.

  3. STICKINESS ─ час що гравець реально провів на карті (з player_stats).
                  Квартилі, % швидких виходів, % тих хто грав ≥60 хв.

  4. RETURN     ─ % гравців які повернулися на сервер у наступні 7 днів
                  після гри на цій карті — "ефект перших вражень".

  5. BALANCE    ─ розподіл результатів warfare-матчів (5:0 vs 3:2).
                  Стомпи vs близькі ігри per мапа.

Запуск:
    docker compose exec -T backend_1 python -m custom_tools.admin_analytics

Параметри (LOOKBACK_DAYS, SERVER_NAME etc.) у блоці CONSTANTS нижче.

Безпечно для прода: тільки SELECT-запити, не пише в БД.
"""
from rcon.models import enter_session
from sqlalchemy import text
from collections import defaultdict
from statistics import median


# ═══════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════

LOOKBACK_DAYS = 180
SERVER_NAME = "HILF UA"

# (1) FILL SPEED
FILL_SEED_MAX_POP = 25          # match starts in seeding if ≤25 players at m.start
FILL_MIN_MATCHES = 3
FILL_THRESHOLDS = (30, 60, 90)

# (2) NET FLOW
FLOW_WINDOW_MIN = 30            # observe 30 min after map switch
FLOW_LATEST_START_HOUR = 22     # cutoff 22:30 Kyiv → window ends ≤ 23:00
FLOW_LATEST_START_MIN = 30
FLOW_MIN_PRESENT = 10
FLOW_MIN_MATCHES = 3

# (3) STICKINESS (session duration)
STICK_MIN_PLAYERS = 50          # require ≥50 unique player-matches per map
STICK_QUICK_THRESHOLD = 15      # ≤15 min = "quick exit"
STICK_LONG_THRESHOLD = 60       # ≥60 min = "engaged"

# (4) RETURN RATE
RETURN_WINDOW_DAYS = 7          # measure return within 7 days
RETURN_MIN_MATCHES = 5
# Skip the same-day window so a long single session doesn't count as a "return"
RETURN_DELAY_HOURS = 12

# (5) BALANCE
BALANCE_MIN_MATCHES = 5
# Imbalance buckets — warfare caps difference (allies - axis)
# stomp = |Δ|≥4 (5:0, 5:1), clear = |Δ|=3 (5:2), close = |Δ|≤2 (3:2)


DOW_UK = {0: "нд", 1: "пн", 2: "вт", 3: "ср", 4: "чт", 5: "пт", 6: "сб"}


# ═══════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════

def pretty_map(name: str) -> str:
    """Strip game-engine suffixes and short region codes from map_name."""
    base = name.lower()
    for sfx in ("_warfare_v2", "_warfare_night", "_offensive_us",
                "_offensive_ger", "_offensive_rus", "_offensive",
                "_warfare", "_skirmish", "_v2"):
        base = base.replace(sfx, "")
    parts = base.split("_")
    if parts and parts[0] in ("phl", "l", "sme", "kha", "car", "kur"):
        base = "_".join(parts[1:])
    return base.replace("_", " ").title()


def layer_tag(name: str) -> str:
    """Short visual marker for layer variants."""
    n = name.lower()
    if "night" in n:           return "🌙"
    if "dusk" in n:            return "🌆"
    if "morning" in n:         return "🌅"
    if "offensive_us" in n:    return "(off-US)"
    if "offensive_ger" in n:   return "(off-GE)"
    if "offensive_rus" in n:   return "(off-RU)"
    if "offensive" in n:       return "(off)"
    return ""


def map_label(name: str, width: int = 26) -> str:
    return (pretty_map(name) + " " + layer_tag(name)).strip()[:width]


def section(title: str) -> None:
    print()
    print("═" * 72)
    print(f"  {title}")
    print("═" * 72)


# ═══════════════════════════════════════════════════════════════════
# (1) FILL SPEED — seed-start matches to N players
# ═══════════════════════════════════════════════════════════════════

FILL_SQL = """
WITH matches AS (
    SELECT id, map_name, start, "end",
           EXTRACT(DOW FROM (start AT TIME ZONE 'UTC') AT TIME ZONE 'Europe/Kyiv')::int AS dow
    FROM map_history
    WHERE start >= NOW() - INTERVAL '{days} days'
      AND "end" IS NOT NULL AND server_number = 1
      AND ("end" - start) BETWEEN INTERVAL '20 minutes' AND INTERVAL '3 hours'
),
events AS (
    SELECT m.id AS match_id, m.map_name, m.start AS m_start, m.dow,
           GREATEST(s.start, m.start) AS evt_time, +1 AS delta
    FROM matches m
    JOIN player_sessions s
      ON s.server_name = '{server}'
     AND s.start <  m."end"
     AND (s."end" IS NULL OR s."end" > m.start)
     AND (s."end" IS NOT NULL OR s.start > m."end" - INTERVAL '4 hours')
    UNION ALL
    SELECT m.id, m.map_name, m.start, m.dow,
           LEAST(s."end", m."end"), -1
    FROM matches m
    JOIN player_sessions s
      ON s.server_name = '{server}'
     AND s.start <  m."end"
     AND s."end" IS NOT NULL AND s."end" > m.start
),
running AS (
    SELECT match_id, map_name, m_start, dow, evt_time,
           SUM(delta) OVER (PARTITION BY match_id ORDER BY evt_time, delta DESC) AS pop
    FROM events
),
fill_times AS (
    SELECT match_id, map_name, m_start, dow,
           MIN(EXTRACT(EPOCH FROM (evt_time - m_start))/60.0) FILTER (WHERE pop >= 30) AS t30,
           MIN(EXTRACT(EPOCH FROM (evt_time - m_start))/60.0) FILTER (WHERE pop >= 60) AS t60,
           MIN(EXTRACT(EPOCH FROM (evt_time - m_start))/60.0) FILTER (WHERE pop >= 90) AS t90,
           MAX(pop) AS peak_pop
    FROM running GROUP BY 1, 2, 3, 4
),
with_seed AS (
    SELECT ft.*,
        (SELECT COUNT(DISTINCT s.playersteamid_id)
         FROM player_sessions s
         WHERE s.server_name = '{server}'
           AND s.start < ft.m_start
           AND ((s."end" IS NOT NULL AND s."end" > ft.m_start)
             OR (s."end" IS NULL AND s.start > ft.m_start - INTERVAL '4 hours'))
        ) AS pop_at_start
    FROM fill_times ft
)
SELECT * FROM with_seed
WHERE peak_pop >= 30 AND pop_at_start <= {seed_max}
"""


def analysis_fill_speed(sess) -> None:
    rows = sess.execute(text(FILL_SQL.format(
        days=LOOKBACK_DAYS, server=SERVER_NAME, seed_max=FILL_SEED_MAX_POP,
    ))).all()

    section(f"(1) ШВИДКІСТЬ НАПОВНЕННЯ — {len(rows)} матчів з seed-старту")
    print(f"     Тільки матчі що стартували з ≤{FILL_SEED_MAX_POP} гравців")
    print(f"     і досягли пік ≥30. Менше хвилин = швидше наповнюється.\n")

    by_map = defaultdict(lambda: {"t30":[], "t60":[], "t90":[]})
    by_dow = defaultdict(lambda: {"t30":[], "t60":[], "t90":[]})
    for r in rows:
        for k, v in [("t30", r.t30), ("t60", r.t60), ("t90", r.t90)]:
            if v is not None:
                by_map[r.map_name][k].append(v)
                by_dow[r.dow][k].append(v)

    # By map
    print("  За картою:")
    print(f"    {'Карта':<26s} {'матчів':>6s} {'до 30':>7s} {'до 60':>7s} {'до 90':>7s}")
    print(f"    {'-'*26} {'-'*6} {'-'*7} {'-'*7} {'-'*7}")
    map_rows = []
    for mp, vals in by_map.items():
        if len(vals["t30"]) < FILL_MIN_MATCHES:
            continue
        map_rows.append((
            mp, len(vals["t30"]),
            median(vals["t30"]) if vals["t30"] else None,
            median(vals["t60"]) if vals["t60"] else None,
            median(vals["t90"]) if vals["t90"] else None,
        ))
    map_rows.sort(key=lambda x: x[2] or 9e9)
    for mp, n, t30, t60, t90 in map_rows:
        s60 = f"{t60:.0f}хв" if t60 is not None else "—"
        s90 = f"{t90:.0f}хв" if t90 is not None else "—"
        print(f"    {map_label(mp):<26s} {n:>6d} {t30:>6.0f}хв {s60:>7s} {s90:>7s}")

    # By day of week
    print()
    print("  За днем тижня:")
    print(f"    {'День':<6s} {'матчів':>6s} {'до 30':>7s} {'до 60':>7s} {'до 90':>7s}")
    print(f"    {'-'*6} {'-'*6} {'-'*7} {'-'*7} {'-'*7}")
    for d in [1,2,3,4,5,6,0]:
        v = by_dow[d]
        if not v["t30"]: continue
        t30 = median(v["t30"])
        t60 = median(v["t60"]) if v["t60"] else None
        t90 = median(v["t90"]) if v["t90"] else None
        s60 = f"{t60:.0f}хв" if t60 is not None else "—"
        s90 = f"{t90:.0f}хв" if t90 is not None else "—"
        print(f"    {DOW_UK[d]:<6s} {len(v['t30']):>6d} {t30:>6.0f}хв {s60:>7s} {s90:>7s}")


# ═══════════════════════════════════════════════════════════════════
# (2) NET FLOW after map switch
# ═══════════════════════════════════════════════════════════════════

FLOW_SQL = """
WITH matches AS (
    SELECT id, map_name, start,
           EXTRACT(DOW    FROM (start AT TIME ZONE 'UTC') AT TIME ZONE 'Europe/Kyiv')::int AS dow,
           EXTRACT(HOUR   FROM (start AT TIME ZONE 'UTC') AT TIME ZONE 'Europe/Kyiv')::int AS hr,
           EXTRACT(MINUTE FROM (start AT TIME ZONE 'UTC') AT TIME ZONE 'Europe/Kyiv')::int AS mn
    FROM map_history
    WHERE start >= NOW() - INTERVAL '{days} days'
      AND server_number = 1 AND "end" IS NOT NULL
)
SELECT m.id, m.map_name, m.dow, m.hr,
    (SELECT COUNT(DISTINCT s.playersteamid_id) FROM player_sessions s
     WHERE s.server_name='{server}' AND s.start < m.start
       AND ((s."end" IS NOT NULL AND s."end" > m.start)
         OR (s."end" IS NULL AND s.start > m.start - INTERVAL '4 hours'))
    ) AS present,
    (SELECT COUNT(DISTINCT s.playersteamid_id) FROM player_sessions s
     WHERE s.server_name='{server}' AND s.start < m.start
       AND s."end" IS NOT NULL AND s."end" > m.start
       AND s."end" <= m.start + INTERVAL '{window} minutes'
    ) AS bailed,
    (SELECT COUNT(DISTINCT s.playersteamid_id) FROM player_sessions s
     WHERE s.server_name='{server}' AND s.start > m.start
       AND s.start <= m.start + INTERVAL '{window} minutes'
    ) AS newcomers
FROM matches m
WHERE m.hr >= 6                                    -- skip post-midnight overflow
  AND (m.hr < {lh} OR (m.hr = {lh} AND m.mn <= {lm}))
"""


def analysis_net_flow(sess) -> None:
    rows = sess.execute(text(FLOW_SQL.format(
        days=LOOKBACK_DAYS, server=SERVER_NAME, window=FLOW_WINDOW_MIN,
        lh=FLOW_LATEST_START_HOUR, lm=FLOW_LATEST_START_MIN,
    ))).all()

    section(f"(2) NET FLOW — рух людей за {FLOW_WINDOW_MIN} хв після зміни карти")
    print(f"     Тільки матчі що стартували ≤{FLOW_LATEST_START_HOUR}:{FLOW_LATEST_START_MIN:02d} Kyiv\n")

    by_map = defaultdict(lambda: {"p":0,"b":0,"n":0,"k":0})
    by_dow = defaultdict(lambda: {"p":0,"b":0,"n":0,"k":0})
    by_hr  = defaultdict(lambda: {"p":0,"b":0,"n":0,"k":0})
    for r in rows:
        if r.present < FLOW_MIN_PRESENT: continue
        for bucket, key in [(by_map, r.map_name), (by_dow, r.dow), (by_hr, r.hr)]:
            bucket[key]["p"] += r.present
            bucket[key]["b"] += r.bailed
            bucket[key]["n"] += r.newcomers
            bucket[key]["k"] += 1

    # By map
    print('  За картою (sort: net asc — спочатку ті що "втрачають"):')
    print(f"    {'Карта':<26s} {'k':>4s} {'∅прис':>6s} {'%вих':>6s} {'%прих':>6s} {'Δнет':>7s}")
    print(f"    {'-'*26} {'-'*4} {'-'*6} {'-'*6} {'-'*6} {'-'*7}")
    rows_m = []
    for mp, d in by_map.items():
        if d["k"] < FLOW_MIN_MATCHES: continue
        ap = d["p"]/d["k"]
        po = 100*d["b"]/d["p"]
        pi = 100*d["n"]/d["p"]
        net = (d["n"]-d["b"])/d["k"]
        rows_m.append((mp, d["k"], ap, po, pi, net))
    rows_m.sort(key=lambda x: x[5])
    for mp, k, ap, po, pi, net in rows_m:
        net_s = f"{net:+.1f}"
        print(f"    {map_label(mp):<26s} {k:>4d} {ap:>6.0f} {po:>5.1f}% {pi:>5.1f}% {net_s:>7s}")

    # By day
    print()
    print("  За днем тижня:")
    print(f"    {'День':<6s} {'k':>4s} {'∅прис':>6s} {'%вих':>6s} {'%прих':>6s} {'Δнет':>7s}")
    print(f"    {'-'*6} {'-'*4} {'-'*6} {'-'*6} {'-'*6} {'-'*7}")
    for dow in [1,2,3,4,5,6,0]:
        d = by_dow[dow]
        if d["k"] < FLOW_MIN_MATCHES: continue
        ap = d["p"]/d["k"]; po=100*d["b"]/d["p"]; pi=100*d["n"]/d["p"]; net=(d["n"]-d["b"])/d["k"]
        print(f"    {DOW_UK[dow]:<6s} {d['k']:>4d} {ap:>6.0f} {po:>5.1f}% {pi:>5.1f}% {net:>+7.1f}")

    # By hour
    print()
    print("  За годиною старту:")
    print(f"    {'Год':<4s} {'k':>4s} {'∅прис':>6s} {'%вих':>6s} {'%прих':>6s} {'Δнет':>7s}")
    print(f"    {'-'*4} {'-'*4} {'-'*6} {'-'*6} {'-'*6} {'-'*7}")
    for hr in sorted(by_hr):
        d = by_hr[hr]
        if d["k"] < FLOW_MIN_MATCHES: continue
        ap = d["p"]/d["k"]; po=100*d["b"]/d["p"]; pi=100*d["n"]/d["p"]; net=(d["n"]-d["b"])/d["k"]
        print(f"    {hr:<4d} {d['k']:>4d} {ap:>6.0f} {po:>5.1f}% {pi:>5.1f}% {net:>+7.1f}")


# ═══════════════════════════════════════════════════════════════════
# (3) STICKINESS — time players spend on each map
# ═══════════════════════════════════════════════════════════════════

STICK_SQL = """
WITH map_players AS (
    SELECT mh.map_name, ps.time_seconds / 60.0 AS minutes
    FROM map_history mh
    JOIN player_stats ps ON ps.map_id = mh.id
    WHERE mh.start >= NOW() - INTERVAL '{days} days'
      AND mh.server_number = 1 AND mh."end" IS NOT NULL
      AND ps.time_seconds > 60
)
SELECT map_name,
    COUNT(*)::int AS player_matches,
    ROUND(PERCENTILE_CONT(0.5)  WITHIN GROUP (ORDER BY minutes)::numeric, 1) AS med,
    ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY minutes)::numeric, 1) AS p25,
    ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY minutes)::numeric, 1) AS p75,
    ROUND((100.0 * COUNT(*) FILTER (WHERE minutes <= {quick}) / COUNT(*))::numeric, 1) AS quick_pct,
    ROUND((100.0 * COUNT(*) FILTER (WHERE minutes >= {long})  / COUNT(*))::numeric, 1) AS long_pct
FROM map_players GROUP BY map_name
HAVING COUNT(*) >= {min_pm}
ORDER BY quick_pct ASC
"""


def analysis_stickiness(sess) -> None:
    rows = sess.execute(text(STICK_SQL.format(
        days=LOOKBACK_DAYS, quick=STICK_QUICK_THRESHOLD,
        long=STICK_LONG_THRESHOLD, min_pm=STICK_MIN_PLAYERS,
    ))).all()

    section("(3) STICKINESS — час гравця на карті (з player_stats)")
    print(f"     ≥{STICK_MIN_PLAYERS} player-matches на карту. Sort: % швидких виходів asc.\n")
    print(f"    {'Карта':<26s} {'player·match':>12s} {'мед':>5s} "
          f"{'25%':>5s} {'75%':>5s} {'≤{q}м':>6s} {'≥{l}м':>6s}".format(
              q=STICK_QUICK_THRESHOLD, l=STICK_LONG_THRESHOLD))
    print(f"    {'-'*26} {'-'*12} {'-'*5} {'-'*5} {'-'*5} {'-'*6} {'-'*6}")
    for r in rows:
        print(f"    {map_label(r.map_name):<26s} {r.player_matches:>12d} "
              f"{r.med:>5.0f} {r.p25:>5.0f} {r.p75:>5.0f} "
              f"{r.quick_pct:>5.1f}% {r.long_pct:>5.1f}%")


# ═══════════════════════════════════════════════════════════════════
# (4) RETURN RATE
# ═══════════════════════════════════════════════════════════════════

RETURN_SQL = """
WITH match_players AS (
    SELECT mh.id, mh.map_name, mh.start, mh."end",
           ps.playersteamid_id
    FROM map_history mh
    JOIN player_stats ps ON ps.map_id = mh.id
    WHERE mh.start >= NOW() - INTERVAL '{days} days'
      AND mh.start <= NOW() - INTERVAL '{ret_days} days'  -- room to observe return
      AND mh.server_number = 1 AND mh."end" IS NOT NULL
      AND ps.time_seconds > 60
),
returns AS (
    SELECT mp.map_name,
           mp.playersteamid_id,
           EXISTS (
               SELECT 1 FROM player_sessions s
               WHERE s.server_name='{server}'
                 AND s.playersteamid_id = mp.playersteamid_id
                 AND s.start > mp."end" + INTERVAL '{delay_h} hours'
                 AND s.start <= mp."end" + INTERVAL '{ret_days} days'
           ) AS came_back
    FROM match_players mp
)
SELECT map_name,
    COUNT(*)::int                                     AS plays,
    ROUND((100.0 * COUNT(*) FILTER (WHERE came_back) / COUNT(*))::numeric, 1)
                                                      AS return_pct
FROM returns GROUP BY map_name
HAVING COUNT(*) >= {min_p}
ORDER BY return_pct DESC
"""


def analysis_return_rate(sess) -> None:
    rows = sess.execute(text(RETURN_SQL.format(
        days=LOOKBACK_DAYS, server=SERVER_NAME,
        ret_days=RETURN_WINDOW_DAYS, delay_h=RETURN_DELAY_HOURS,
        min_p=STICK_MIN_PLAYERS,
    ))).all()

    section(f"(4) RETURN RATE — % гравців які повернулися протягом {RETURN_WINDOW_DAYS} днів")
    print(f"     Затримка ≥{RETURN_DELAY_HOURS} год (щоб не лічити продовжену сесію за повернення)")
    print(f"     Sort: return_pct desc (вгорі — найкращі за утриманням).\n")
    print(f"    {'Карта':<26s} {'player·match':>12s} {'%повернулися':>14s}")
    print(f"    {'-'*26} {'-'*12} {'-'*14}")
    # Compute global average for baseline
    if rows:
        total_plays = sum(r.plays for r in rows)
        total_back = sum(r.plays * r.return_pct / 100 for r in rows)
        global_avg = 100 * total_back / total_plays
    else:
        global_avg = 0
    for r in rows:
        marker = "⬆️" if r.return_pct > global_avg + 2 else ("⬇️" if r.return_pct < global_avg - 2 else "  ")
        print(f"    {map_label(r.map_name):<26s} {r.plays:>12d} {r.return_pct:>11.1f}% {marker}")
    print()
    print(f"     ── базовий рівень повернення на сервері: {global_avg:.1f}% ──")


# ═══════════════════════════════════════════════════════════════════
# (5) BALANCE — match result distribution
# ═══════════════════════════════════════════════════════════════════

BALANCE_SQL = """
SELECT map_name, result
FROM map_history
WHERE start >= NOW() - INTERVAL '{days} days'
  AND server_number = 1 AND "end" IS NOT NULL
  AND result IS NOT NULL
  AND map_name NOT LIKE '%%skirmish%%'
  AND result ? 'Axis' AND result ? 'Allied'
"""


def analysis_balance(sess) -> None:
    rows = sess.execute(text(BALANCE_SQL.format(days=LOOKBACK_DAYS))).all()

    by_map = defaultdict(lambda: {
        "k":0, "stomp":0, "clear":0, "close":0, "tie":0,
        "allied_wins":0, "axis_wins":0, "sum_diff":0,
    })
    for r in rows:
        try:
            a = int(r.result.get("Allied", 0))
            x = int(r.result.get("Axis", 0))
        except (TypeError, AttributeError):
            continue
        if a + x < 2:   # incomplete / seeding-only match
            continue
        diff = abs(a - x)
        d = by_map[r.map_name]
        d["k"] += 1
        d["sum_diff"] += diff
        if diff >= 4:   d["stomp"] += 1
        elif diff == 3: d["clear"] += 1
        elif diff <= 2 and (a == 5 or x == 5):
            d["close"] += 1
        else:           d["tie"] += 1
        if a > x: d["allied_wins"] += 1
        elif x > a: d["axis_wins"] += 1

    section("(5) BALANCE — розподіл результатів warfare-матчів")
    print(f"     стомп = різниця ≥4 кепів (5:0/5:1), стандарт = 5:2,")
    print(f"     близько = 5:3/5:4, тай = ніхто не дійшов до 5\n")
    print(f"    {'Карта':<26s} {'k':>4s} {'∅Δ':>4s} "
          f"{'стомп':>7s} {'станд':>7s} {'близ.':>7s} {'тай':>5s} "
          f"{'AЛ':>4s} {'AХ':>4s}")
    print(f"    {'-'*26} {'-'*4} {'-'*4} {'-'*7} {'-'*7} {'-'*7} {'-'*5} {'-'*4} {'-'*4}")
    map_rows = []
    for mp, d in by_map.items():
        if d["k"] < BALANCE_MIN_MATCHES: continue
        avg_diff = d["sum_diff"] / d["k"]
        map_rows.append((mp, d, avg_diff))
    # Sort by stomp % desc (worst balance first)
    map_rows.sort(key=lambda x: -x[1]["stomp"] / x[1]["k"])
    for mp, d, avg in map_rows:
        n = d["k"]
        sp = 100*d["stomp"]/n
        cp = 100*d["clear"]/n
        clp = 100*d["close"]/n
        tp = 100*d["tie"]/n
        print(f"    {map_label(mp):<26s} {n:>4d} {avg:>4.1f} "
              f"{sp:>6.1f}% {cp:>6.1f}% {clp:>6.1f}% {tp:>4.1f}% "
              f"{d['allied_wins']:>4d} {d['axis_wins']:>4d}")


# ═══════════════════════════════════════════════════════════════════
# (6) COMPOSITE SCORECARD + LATE-EVENING CHAMPIONS
# ═══════════════════════════════════════════════════════════════════
#
# Bundles the per-map metrics from (1)-(5) into a single ranking.
# Also flags "late-evening champions" — maps whose net flow stays positive
# during hours when the overall server bleeds players (typically 22:00+ Kyiv).
#
# Three sub-tables:
#   A. SEEDING SCORE     — for matches starting with ≤25 players (server empty):
#                          how fast do they fill, and do players return?
#   B. PRIME SCORE       — for matches at full pop (≥30 at switch):
#                          do players stay, return, and is it balanced?
#   C. LATE-EVENING HOLD — for matches starting in late hours (Kyiv 22-01):
#                          which maps still bring net+ (newcomers > leavers)?

LATE_EVENING_START_HOUR = 23   # Kyiv hours [23, 26) = 23, 0, 1
LATE_EVENING_END_HOUR = 26     # exclusive — covers the bedtime-drain zone

COMPOSITE_LATE_SQL = """
WITH late_matches AS (
    SELECT id, map_name, start,
           EXTRACT(HOUR FROM (start AT TIME ZONE 'UTC') AT TIME ZONE 'Europe/Kyiv')::int AS kh
    FROM map_history
    WHERE start >= NOW() - INTERVAL '{days} days'
      AND server_number = 1 AND "end" IS NOT NULL
)
SELECT m.id, m.map_name, m.kh,
    (SELECT COUNT(DISTINCT s.playersteamid_id) FROM player_sessions s
     WHERE s.server_name='{server}' AND s.start < m.start
       AND ((s."end" IS NOT NULL AND s."end" > m.start)
         OR (s."end" IS NULL AND s.start > m.start - INTERVAL '4 hours'))
    ) AS present,
    (SELECT COUNT(DISTINCT s.playersteamid_id) FROM player_sessions s
     WHERE s.server_name='{server}' AND s.start < m.start
       AND s."end" IS NOT NULL AND s."end" > m.start
       AND s."end" <= m.start + INTERVAL '30 minutes') AS bailed,
    (SELECT COUNT(DISTINCT s.playersteamid_id) FROM player_sessions s
     WHERE s.server_name='{server}' AND s.start > m.start
       AND s.start <= m.start + INTERVAL '30 minutes') AS newcomers
FROM late_matches m
WHERE (m.kh >= {lh_start} OR m.kh < ({lh_end} - 24))
"""


def analysis_composite(sess) -> None:
    """Build a per-map scorecard combining everything we've learned."""
    section("(6) MAP SCORECARD — об'єднаний рейтинг карт")

    # Pull all per-map data we've already computed by re-running compact queries
    # and merging into one dict keyed by map_name.
    scorecard = defaultdict(dict)

    # — Stickiness (median min, %quick, %long)
    rows = sess.execute(text(STICK_SQL.format(
        days=LOOKBACK_DAYS, quick=STICK_QUICK_THRESHOLD,
        long=STICK_LONG_THRESHOLD, min_pm=STICK_MIN_PLAYERS,
    ))).all()
    for r in rows:
        scorecard[r.map_name].update(
            stick_n=r.player_matches, med=float(r.med),
            quick_pct=float(r.quick_pct), long_pct=float(r.long_pct),
        )

    # — Return rate
    rows = sess.execute(text(RETURN_SQL.format(
        days=LOOKBACK_DAYS, server=SERVER_NAME,
        ret_days=RETURN_WINDOW_DAYS, delay_h=RETURN_DELAY_HOURS,
        min_p=STICK_MIN_PLAYERS,
    ))).all()
    if rows:
        total_plays = sum(r.plays for r in rows)
        total_back  = sum(r.plays * float(r.return_pct) / 100 for r in rows)
        return_baseline = 100 * total_back / total_plays
    else:
        return_baseline = 0.0
    for r in rows:
        scorecard[r.map_name]["return_pct"] = float(r.return_pct)

    # — Net flow (overall — uses FLOW_LATEST_START_HOUR cutoff for "evening")
    rows = sess.execute(text(FLOW_SQL.format(
        days=LOOKBACK_DAYS, server=SERVER_NAME, window=FLOW_WINDOW_MIN,
        lh=FLOW_LATEST_START_HOUR, lm=FLOW_LATEST_START_MIN,
    ))).all()
    flow_acc = defaultdict(lambda: {"p":0,"b":0,"n":0,"k":0})
    for r in rows:
        if r.present < FLOW_MIN_PRESENT: continue
        flow_acc[r.map_name]["p"] += r.present
        flow_acc[r.map_name]["b"] += r.bailed
        flow_acc[r.map_name]["n"] += r.newcomers
        flow_acc[r.map_name]["k"] += 1
    for mp, d in flow_acc.items():
        if d["k"] < FLOW_MIN_MATCHES: continue
        scorecard[mp]["flow_k"]   = d["k"]
        scorecard[mp]["flow_net"] = (d["n"] - d["b"]) / d["k"]

    # — Balance (stomp %)
    rows = sess.execute(text(BALANCE_SQL.format(days=LOOKBACK_DAYS))).all()
    bal_acc = defaultdict(lambda: {"k":0,"stomp":0})
    for r in rows:
        try:
            a, x = int(r.result.get("Allied",0)), int(r.result.get("Axis",0))
        except (TypeError, AttributeError):
            continue
        if a + x < 2: continue
        bal_acc[r.map_name]["k"] += 1
        if abs(a - x) >= 4:
            bal_acc[r.map_name]["stomp"] += 1
    for mp, d in bal_acc.items():
        if d["k"] < BALANCE_MIN_MATCHES: continue
        scorecard[mp]["stomp_pct"] = 100 * d["stomp"] / d["k"]

    # — Late-evening flow (Kyiv 22:00 onwards)
    rows = sess.execute(text(COMPOSITE_LATE_SQL.format(
        days=LOOKBACK_DAYS, server=SERVER_NAME,
        lh_start=LATE_EVENING_START_HOUR, lh_end=LATE_EVENING_END_HOUR,
    ))).all()
    late_acc = defaultdict(lambda: {"p":0,"b":0,"n":0,"k":0})
    for r in rows:
        if r.present < FLOW_MIN_PRESENT: continue
        late_acc[r.map_name]["p"] += r.present
        late_acc[r.map_name]["b"] += r.bailed
        late_acc[r.map_name]["n"] += r.newcomers
        late_acc[r.map_name]["k"] += 1
    for mp, d in late_acc.items():
        if d["k"] < FLOW_MIN_MATCHES: continue
        scorecard[mp]["late_k"]   = d["k"]
        scorecard[mp]["late_net"] = (d["n"] - d["b"]) / d["k"]

    # ── 6A. OVERALL SCORECARD ──────────────────────────────────────
    # Only maps with at least the stickiness data (≥ STICK_MIN_PLAYERS).
    print(f"\n  6A. SCORECARD — карти що мають ≥{STICK_MIN_PLAYERS} player-matches:\n")
    hdr = (f"    {'Карта':<26s} "
           f"{'мед':>4s} {'%швид':>6s} {'%>60':>5s} "
           f"{'%верн':>6s} {'Δнет':>6s} {'%стомп':>7s} {'Δпізно':>7s}")
    print(hdr)
    print(f"    {'-'*26} {'-'*4} {'-'*6} {'-'*5} {'-'*6} {'-'*6} {'-'*7} {'-'*7}")

    def composite_score(d):
        """Lower = worse. Combines: return delta, net flow, stickiness, balance."""
        score = 0.0
        if "return_pct" in d:
            score += (float(d["return_pct"]) - return_baseline) * 1.5
        if "flow_net" in d:
            score += float(d["flow_net"]) * 0.6
        if "long_pct" in d:
            score += (float(d["long_pct"]) - 10) * 0.5
        if "quick_pct" in d:
            score -= (float(d["quick_pct"]) - 28) * 0.5
        if "stomp_pct" in d:
            score -= (float(d["stomp_pct"]) - 40) * 0.15
        if "late_net" in d:
            score += float(d["late_net"]) * 0.4   # bonus for late-evening hold
        return score

    items = [(mp, d, composite_score(d)) for mp, d in scorecard.items()
             if "med" in d]    # require stickiness data
    items.sort(key=lambda x: -x[2])

    for mp, d, sc in items:
        med    = f"{d.get('med', 0):.0f}"
        qp     = f"{d.get('quick_pct', 0):.1f}%"
        lp     = f"{d.get('long_pct', 0):.1f}%"
        rp     = f"{d.get('return_pct', 0):.1f}%" if "return_pct" in d else "  —  "
        net    = f"{d.get('flow_net'):+.1f}" if "flow_net" in d else "  —  "
        sm     = f"{d.get('stomp_pct'):.1f}%" if "stomp_pct" in d else "  —  "
        ln     = f"{d.get('late_net'):+.1f}" if "late_net" in d else "  —  "
        print(f"    {map_label(mp):<26s} {med:>4s} {qp:>6s} {lp:>5s} "
              f"{rp:>6s} {net:>6s} {sm:>7s} {ln:>7s}")

    print(f"\n     Базовий return: {return_baseline:.1f}%. Sort: композитний скор desc.")
    print(f"     Колонки: мед=медіана хв на карті, %швид=≤15хв виходи,")
    print(f"              %>60=залипли ≥60хв, %верн=повернулись за 7 днів,")
    print(f"              Δнет=net flow (зміна-карти), %стомп=частка 5:0/5:1,")
    print(f"              Δпізно=net flow у пізні години (Київ ≥22:00).")

    # ── 6B. LATE-EVENING CHAMPIONS ─────────────────────────────────
    print(f"\n  6B. ПІЗНО-ВЕЧІРНІ ЧЕМПІОНИ (старт матчу у Київ {LATE_EVENING_START_HOUR}:00+):\n")
    print(f"     Карти що ТРИМАЮТЬ людей коли інші зливаються.")
    print(f"     Δпізно > 0 = новачки заходять навіть пізно вночі.\n")
    late_items = [(mp, d) for mp, d in scorecard.items() if "late_net" in d]
    late_items.sort(key=lambda x: -x[1]["late_net"])
    print(f"    {'Карта':<26s} {'матчів':>6s} {'Δпізно':>7s} {'%верн':>6s}")
    print(f"    {'-'*26} {'-'*6} {'-'*7} {'-'*6}")
    for mp, d in late_items:
        ret = f"{d.get('return_pct'):.1f}%" if "return_pct" in d else "  —  "
        print(f"    {map_label(mp):<26s} {d['late_k']:>6d} "
              f"{d['late_net']:>+7.1f} {ret:>6s}")


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main() -> None:
    print(f"╔{'═'*70}╗")
    print(f"║  HLL Server Analytics — HILF UA, last {LOOKBACK_DAYS} days{' '*(70-44-len(str(LOOKBACK_DAYS)))}║")
    print(f"╚{'═'*70}╝")

    with enter_session() as sess:
        analysis_fill_speed(sess)
        analysis_net_flow(sess)
        analysis_stickiness(sess)
        analysis_return_rate(sess)
        analysis_balance(sess)
        analysis_composite(sess)

    print()
    print("═" * 72)
    print("Готово. Усі цифри — read-only SELECT, БД не змінювалась.")
    print("═" * 72)


if __name__ == "__main__":
    main()
