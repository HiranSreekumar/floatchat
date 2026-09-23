from typing import Optional, Literal
from pydantic import BaseModel, Field


class QueryIntent(BaseModel):
    variable: Literal["temperature", "salinity", "pressure", "temperature_and_salinity"] = "temperature_and_salinity"
    metric: Literal["profile", "average", "min", "max", "count", "timeseries"] = "profile"

    lon_min: float
    lon_max: float
    lat_min: float
    lat_max: float
    resolved_location_label: str = Field(..., description="Human-readable resolved place name")

    start_date: str
    end_date: str
    resolved_time_label: str = Field(..., description="Human-readable resolved time window")

    pres_min: Optional[float] = None
    pres_max: Optional[float] = None

    clarification_needed: Optional[str] = Field(
        None, description="Set instead of guessing if location/time is too ambiguous to resolve confidently."
    )


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    intent: Optional[dict] = None
    sql: Optional[str] = None
    row_count: int = 0
    results: list = []
    profile_locations: list = []
    depth_profiles: list = []
    explanation: str = ""
    clarification: Optional[str] = None
    used_synthetic_data: bool = False
