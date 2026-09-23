"""
Claude call #1: natural language question -> structured QueryIntent, via
forced tool-use for reliable structured output. Never sees real ocean data.
"""
from datetime import date

import anthropic

from .config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from .geo import gazetteer_prompt_block
from .schemas import QueryIntent

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

INTENT_TOOL = {
    "name": "emit_query_intent",
    "description": "Emit the structured query intent parsed from the user's ocean-data question.",
    "input_schema": {
        "type": "object",
        "properties": {
            "variable": {"type": "string", "enum": ["temperature", "salinity", "pressure", "temperature_and_salinity"]},
            "metric": {
                "type": "string",
                "enum": ["profile", "average", "min", "max", "count", "timeseries"],
                "description": "'profile' = depth-resolved profiles; 'average'/'min'/'max' = an aggregate scalar; 'count' = number of profiles/floats; 'timeseries' = grouped by month.",
            },
            "lon_min": {"type": "number"}, "lon_max": {"type": "number"},
            "lat_min": {"type": "number"}, "lat_max": {"type": "number"},
            "resolved_location_label": {"type": "string"},
            "start_date": {"type": "string", "description": "ISO date YYYY-MM-DD"},
            "end_date": {"type": "string", "description": "ISO date YYYY-MM-DD"},
            "resolved_time_label": {"type": "string"},
            "pres_min": {"type": "number"}, "pres_max": {"type": "number"},
            "clarification_needed": {
                "type": "string",
                "description": "If location/time is too ambiguous to resolve responsibly, explain what's needed here INSTEAD of guessing coordinates.",
            },
        },
        "required": ["variable", "metric", "lon_min", "lon_max", "lat_min", "lat_max",
                     "resolved_location_label", "start_date", "end_date", "resolved_time_label"],
    },
}


def _system_prompt() -> str:
    today = date.today().isoformat()
    return f"""You are the query-understanding module of FloatChat, a system for querying \
India's ARGO ocean float network. Your ONLY job is to convert a user's natural-language \
question into a structured query intent by calling the emit_query_intent tool. You do NOT \
answer the question and you have NO access to actual ocean data.

Today's date is {today}. Use it to resolve relative time expressions.

Indian monsoon convention (use this unless the user specifies otherwise):
- Southwest ("summer") monsoon: June-September
- Northeast monsoon (mainly Bay of Bengal / Tamil Nadu coast): October-December
- Pre-monsoon: March-May
- Post-monsoon / winter: December-February
"Last monsoon season" means the most recently COMPLETED Jun-Sep window relative to today.

Known reference coordinates for grounding geographic reasoning — do not invent coordinates \
for these named places, and interpolate sensibly for compound descriptions:
{gazetteer_prompt_block()}

Geographic reasoning rules:
- For "off <city>" or "near <city>", build a bounding box roughly 1.5-2.5 degrees around the \
reference point (about 150-250km), wider for offshore/deep-water phrasing.
- If the user names a place NOT in the table and you are not highly confident of its coastal \
coordinates, do not guess — set clarification_needed instead.

Temporal reasoning rules:
- Resolve relative dates against today's date.
- A bare year means Jan 1 - Dec 31 of that year unless a season is also specified.

Query shaping rules:
- Default metric is 'profile' unless the user clearly asks for an average/min/max/count/trend.
- Keep the resolved bounding box reasonably tight; Argovis limits results to <1000 profiles per \
date-range/region query.
- Always populate resolved_location_label and resolved_time_label with a short human-readable \
summary (shown to the user for transparency).

Call emit_query_intent exactly once."""


def parse_query(user_message: str) -> QueryIntent:
    resp = _client.messages.create(
        model=CLAUDE_MODEL, max_tokens=1024, system=_system_prompt(),
        tools=[INTENT_TOOL], tool_choice={"type": "tool", "name": "emit_query_intent"},
        messages=[{"role": "user", "content": user_message}],
    )
    for block in resp.content:
        if block.type == "tool_use" and block.name == "emit_query_intent":
            return QueryIntent(**block.input)
    raise RuntimeError("Claude did not return a query intent tool call.")
