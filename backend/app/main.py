"""
FloatChat backend. Pipeline per request to /api/chat:
  1. nl_parser.parse_query()       -- Claude call #1: question -> structured intent
  2. sql_builder.build_and_run()   -- deterministic SQL against Postgres (no LLM)
  3. explainer.explain()           -- Claude call #2: real results -> grounded NL answer
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .db import init_db, row_counts
from .schemas import ChatRequest, ChatResponse
from .nl_parser import parse_query
from .sql_builder import build_and_run, build_map_and_chart_payloads
from .explainer import explain
from . import demo_data

app = FastAPI(title="FloatChat API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # demo only — restrict to your frontend's domain in production
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup():
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok", **row_counts()}


@app.post("/api/demo-data/load")
def load_demo_data():
    demo_data.generate_and_load()
    return {"loaded": True, **row_counts()}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(400, "Empty message")

    try:
        intent = parse_query(req.message)
    except Exception as e:
        raise HTTPException(502, f"Failed to parse query intent: {e}")

    if intent.clarification_needed:
        return ChatResponse(intent=intent.model_dump(), clarification=intent.clarification_needed, explanation=intent.clarification_needed)

    result = build_and_run(intent)
    locations, depth_profiles = build_map_and_chart_payloads(intent, result)

    try:
        explanation = explain(req.message, intent, result)
    except Exception as e:
        explanation = f"(Explanation step failed: {e}) Raw result rows: {result.row_count}"

    return ChatResponse(
        intent=intent.model_dump(), sql=result.sql, row_count=result.row_count,
        results=result.rows[:200], profile_locations=locations, depth_profiles=depth_profiles,
        explanation=explanation, used_synthetic_data=result.used_synthetic_data,
    )
