"""
Gemini call #2: real SQL results -> grounded natural-language explanation.
Sees ONLY actual numbers computed from the database; never invents figures.
"""
import json

from google import genai

from .config import GEMINI_API_KEY, GEMINI_MODEL
from .schemas import QueryIntent
from .sql_builder import QueryResult


client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """You are the explanation module of FloatChat. You will be given:
1. The user's original question
2. The structured query intent resolved from it
3. The ACTUAL result rows returned by a SQL query against a real ARGO float database

Write a short, clear, natural-language answer (3-6 sentences, plus a compact bullet list of
key numbers if helpful) grounded STRICTLY in the provided result data. Rules:
- Never state a number that is not present in, or a direct arithmetic summary of, the provided rows.
- If the result set is empty, say plainly that no matching float profiles were found in that
  region/time window, and suggest one concrete way to broaden the query.
- If the data is flagged as synthetic/demo data, mention once, briefly, that these are
  illustrative demo profiles rather than a live Argovis pull.
- Round numbers sensibly (temperature to 1 decimal, salinity to 2 decimals, depth to whole meters).
- Use oceanographic context (mixed layer, thermocline, halocline) only when it directly explains
  the numbers shown.
- Do not mention SQL, databases, or pipeline internals - write as if reporting findings from
  the float data."""


def explain(user_message: str, intent: QueryIntent, result: QueryResult) -> str:
    payload = _summarize_for_prompt(intent, result)

    user_content = json.dumps({
        "user_question": user_message,
        "resolved_intent": intent.model_dump(),
        "result_summary": payload,
        "is_synthetic_demo_data": result.used_synthetic_data,
    }, indent=2, default=str)

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=f"{SYSTEM_PROMPT}\n\nData to analyze:\n{user_content}",
        config={
            "temperature": 0.2,
        },
    )

    return response.text.strip()


def _summarize_for_prompt(intent: QueryIntent, result: QueryResult) -> dict:
    if intent.metric != "profile":
        return {"rows": result.rows, "row_count": result.row_count}

    rows = result.rows

    if not rows:
        return {"row_count": 0, "profiles_found": 0}

    profile_ids = {r["profile_id"] for r in rows}

    temps = [
        r["temperature"]
        for r in rows
        if r["temperature"] is not None
    ]

    sals = [
        r["salinity"]
        for r in rows
        if r["salinity"] is not None
    ]

    surface_rows = [
        r for r in rows
        if r["pressure"] is not None and r["pressure"] <= 10
    ]

    deep_rows = [
        r for r in rows
        if r["pressure"] is not None and r["pressure"] >= 500
    ]

    def stats(vals):
        if not vals:
            return None

        return {
            "min": round(min(vals), 3),
            "max": round(max(vals), 3),
            "avg": round(sum(vals) / len(vals), 3),
            "n": len(vals),
        }

    return {
        "row_count": result.row_count,
        "profiles_found": len(profile_ids),
        "date_range_covered": (
            sorted({r["profile_date"] for r in rows})[:1]
            + sorted({r["profile_date"] for r in rows})[-1:]
        ),
        "surface_temperature_c": stats([
            r["temperature"]
            for r in surface_rows
            if r["temperature"] is not None
        ]),
        "surface_salinity_psu": stats([
            r["salinity"]
            for r in surface_rows
            if r["salinity"] is not None
        ]),
        "deep_temperature_c_below_500dbar": stats([
            r["temperature"]
            for r in deep_rows
            if r["temperature"] is not None
        ]),
        "overall_temperature_c": stats(temps),
        "overall_salinity_psu": stats(sals),
    }