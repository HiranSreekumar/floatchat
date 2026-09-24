"""
Central configuration for FloatChat.
All secrets/config come from environment variables (see .env.example).
"""
import os
from dotenv import load_dotenv

load_dotenv()

# --- Gemini ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

# --- Argovis ---
ARGOVIS_BASE_URL = os.getenv("ARGOVIS_BASE_URL", "https://argovis-api.colorado.edu")
ARGOVIS_API_KEY = os.getenv("ARGOVIS_API_KEY", "")

# --- Database (PostgreSQL) ---
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/floatchat"
)

# --- Behavior ---
USE_LIVE_ARGOVIS = os.getenv("USE_LIVE_ARGOVIS", "true").lower() == "true"