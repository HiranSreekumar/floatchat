"""
Deterministic translation of a QueryIntent into parameterized SQL, and
execution against PostgreSQL. NO LLM involvement anywhere in this file.
"""
from dataclasses import dataclass

from .db import get_conn, execute
from .schemas import QueryIntent


@dataclass
class QueryResult:
    sql: str
    params: tuple
    rows: list
    row_count: int
    used_synthetic_data: bool


def build_and_run(intent: QueryIntent) -> QueryResult:
    where = ["p.lon BETWEEN %s AND %s", "p.lat BETWEEN %s AND %s", "p.profile_date BETWEEN %s AND %s"]
    params = [intent.lon_min, intent.lon_max, intent.lat_min, intent.lat_max, intent.start_date, intent.end_date]

    if intent.pres_min is not None:
        where.append("m.pressure >= %s")
        params.append(intent.pres_min)
    if intent.pres_max is not None:
        where.append("m.pressure <= %s")
        params.append(intent.pres_max)

    where_sql = " AND ".join(where)

    if intent.metric == "count":
        sql = f"""
            SELECT COUNT(DISTINCT p.profile_id) AS profile_count,
                   COUNT(DISTINCT p.platform_id) AS float_count
            FROM profiles p JOIN measurements m ON m.profile_id = p.profile_id
            WHERE {where_sql}
        """
    elif intent.metric in ("average", "min", "max"):
        agg = {"average": "AVG", "min": "MIN", "max": "MAX"}[intent.metric]
        cols = []
        if intent.variable in ("temperature", "temperature_and_salinity"):
            cols.append(f"{agg}(m.temperature) AS temperature_{intent.metric}")
        if intent.variable in ("salinity", "temperature_and_salinity"):
            cols.append(f"{agg}(m.salinity) AS salinity_{intent.metric}")
        if intent.variable == "pressure":
            cols.append(f"{agg}(m.pressure) AS pressure_{intent.metric}")
        sql = f"""
            SELECT {', '.join(cols)}, COUNT(DISTINCT p.profile_id) AS profile_count
            FROM profiles p JOIN measurements m ON m.profile_id = p.profile_id
            WHERE {where_sql}
        """
    elif intent.metric == "timeseries":
        agg_col = "m.temperature" if intent.variable != "salinity" else "m.salinity"
        sql = f"""
            SELECT TO_CHAR(p.profile_date, 'YYYY-MM') AS month,
                   AVG({agg_col}) AS avg_value,
                   COUNT(DISTINCT p.profile_id) AS profile_count
            FROM profiles p JOIN measurements m ON m.profile_id = p.profile_id
            WHERE {where_sql}
            GROUP BY month ORDER BY month
        """
    else:
        sql = f"""
            SELECT p.profile_id, p.platform_id, p.lat, p.lon, p.profile_date, p.is_synthetic,
                   m.pressure, m.temperature, m.salinity
            FROM profiles p JOIN measurements m ON m.profile_id = p.profile_id
            WHERE {where_sql}
            ORDER BY p.profile_date, p.profile_id, m.pressure
            LIMIT 5000
        """

    with get_conn() as conn:
        rows = execute(conn, sql, params)

    for r in rows:
        if "profile_date" in r and r["profile_date"] is not None:
            r["profile_date"] = r["profile_date"].isoformat()

    used_synthetic = any(r.get("is_synthetic") for r in rows) if intent.metric == "profile" else _any_synthetic_in_range(intent)

    return QueryResult(sql=sql.strip(), params=tuple(params), rows=rows, row_count=len(rows), used_synthetic_data=used_synthetic)


def _any_synthetic_in_range(intent: QueryIntent) -> bool:
    with get_conn() as conn:
        rows = execute(
            conn,
            """SELECT COUNT(*) c FROM profiles
               WHERE lon BETWEEN %s AND %s AND lat BETWEEN %s AND %s
                 AND profile_date BETWEEN %s AND %s AND is_synthetic = TRUE""",
            (intent.lon_min, intent.lon_max, intent.lat_min, intent.lat_max, intent.start_date, intent.end_date),
        )
        return rows[0]["c"] > 0


def build_map_and_chart_payloads(intent: QueryIntent, result: QueryResult):
    if intent.metric != "profile":
        return [], []

    profiles = {}
    for r in result.rows:
        pid = r["profile_id"]
        if pid not in profiles:
            profiles[pid] = {
                "profile_id": pid, "platform_id": r["platform_id"], "lat": r["lat"], "lon": r["lon"],
                "date": r["profile_date"], "is_synthetic": bool(r["is_synthetic"]), "levels": [],
            }
        profiles[pid]["levels"].append({"pressure": r["pressure"], "temperature": r["temperature"], "salinity": r["salinity"]})

    profile_list = list(profiles.values())
    locations = [{"profile_id": p["profile_id"], "lat": p["lat"], "lon": p["lon"], "date": p["date"], "platform_id": p["platform_id"]} for p in profile_list]
    depth_profiles = profile_list[:25]
    return locations, depth_profiles
