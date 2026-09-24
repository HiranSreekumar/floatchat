"""
Gemini call #1: natural language question -> structured QueryIntent.
Never sees real ocean data.
"""

from datetime import date
import json
from google import genai

from .config import GEMINI_API_KEY, GEMINI_MODEL
from .geo import gazetteer_prompt_block
from .schemas import QueryIntent


client = genai.Client(api_key=GEMINI_API_KEY)


def _system_prompt() -> str:
    today = date.today().isoformat()

    return f"""You are the query-understanding module of FloatChat, a system for querying
India's ARGO ocean float network. Your ONLY job is to convert a user's natural-language
question into a structured JSON query intent. You do NOT answer the question and you have
NO access to actual ocean data.

Today's date is {today}. Use it to resolve relative time expressions.

Indian monsoon convention (use this unless the user specifies otherwise):
- Southwest ("summer") monsoon: June-September
- Northeast monsoon (mainly Bay of Bengal / Tamil Nadu coast): October-December
- Pre-monsoon: March-May
- Post-monsoon / winter: December-February

"Last monsoon season" means the most recently COMPLETED Jun-Sep window relative to today.

Known reference coordinates for grounding geographic reasoning - do not invent coordinates
for these named places, and interpolate sensibly for compound descriptions:

{gazetteer_prompt_block()}

Geographic reasoning rules:
- For "off <city>" or "near <city>", build a bounding box roughly 1.5-2.5 degrees around the
reference point (about 150-250km), wider for offshore/deep-water phrasing.
- If the user names a place NOT in the table and you are not highly confident of its coastal
coordinates, do not guess - set clarification_needed instead.

Temporal reasoning rules:
- Resolve relative dates against today's date.
- A bare year means Jan 1 - Dec 31 of that year unless a season is also specified.

Query shaping rules:
- Default metric is 'profile' unless the user clearly asks for an average/min/max/count/trend.
- Keep the resolved bounding box reasonably tight; Argovis limits results to <1000 profiles per
date-range/region query.
- Always populate resolved_location_label and resolved_time_label with a short human-readable
summary (shown to the user for transparency).

Return ONLY valid JSON with these fields:

{{
  "variable": "temperature" | "salinity" | "pressure" | "temperature_and_salinity",
  "metric": "profile" | "average" | "min" | "max" | "count" | "timeseries",
  "lon_min": number,
  "lon_max": number,
  "lat_min": number,
  "lat_max": number,
  "resolved_location_label": string,
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "resolved_time_label": string,
  "pres_min": number or null,
  "pres_max": number or null,
  "clarification_needed": string or null
}}

Do not include markdown fences or any explanation outside the JSON."""


def parse_query(user_message: str) -> QueryIntent:
    prompt = _system_prompt()

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=f"{prompt}\n\nUser question:\n{user_message}",
        config={
            "temperature": 0,
            "response_mime_type": "application/json",
        },
    )

    try:
        data = json.loads(response.text)
        return QueryIntent(**data)
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise RuntimeError(
            f"Gemini did not return a valid query intent: {exc}"
        ) from exc