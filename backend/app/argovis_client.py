"""
Client for the real Argovis /profiles API (https://argovis-api.colorado.edu).
Plain deterministic HTTP client — no LLM involvement.
"""
from typing import Optional
import httpx

from .config import ARGOVIS_BASE_URL, ARGOVIS_API_KEY


class ArgovisError(RuntimeError):
    pass


def _headers():
    headers = {"Accept": "application/json"}
    if ARGOVIS_API_KEY:
        headers["x-argokey"] = ARGOVIS_API_KEY
    return headers


def fetch_profiles(
    start_date: str,
    end_date: str,
    box: Optional[list] = None,
    polygon: Optional[list] = None,
    pres_range: Optional[tuple] = None,
    data_vars: str = "temperature,pressure,salinity",
    timeout: float = 30.0,
) -> list[dict]:
    params = {"startDate": start_date, "endDate": end_date, "data": data_vars}
    if box:
        params["box"] = _fmt(box)
    elif polygon:
        params["polygon"] = _fmt(polygon)
    if pres_range:
        params["presRange"] = f"{pres_range[0]},{pres_range[1]}"

    url = f"{ARGOVIS_BASE_URL}/profiles"
    try:
        resp = httpx.get(url, params=params, headers=_headers(), timeout=timeout)
    except httpx.HTTPError as e:
        raise ArgovisError(f"Network error contacting Argovis: {e}") from e

    if resp.status_code == 400:
        raise ArgovisError(
            f"Argovis rejected the query (HTTP 400) — likely >1000 profiles matched. "
            f"Narrow the date range or bounding box. Request: {resp.request.url}"
        )
    if resp.status_code != 200:
        raise ArgovisError(f"Argovis API error {resp.status_code}: {resp.text[:500]}")
    return resp.json()


def _fmt(coord_list: list) -> str:
    return "[" + ",".join(f"[{lon},{lat}]" for lon, lat in coord_list) + "]"


def normalize_profile(raw: dict) -> dict:
    lon, lat = raw["geolocation"]["coordinates"]
    levels = []
    for level in raw.get("data", []):
        pres = level.get("pres")
        temp = level.get("temp")
        psal = level.get("psal")
        if pres is not None:
            levels.append((pres, temp, psal))
    return {
        "profile_id": raw.get("_id"),
        "platform_id": str(raw.get("platform_id") or raw.get("platform") or "unknown"),
        "lat": lat,
        "lon": lon,
        "date": (raw.get("timestamp") or "")[:10],
        "levels": levels,
    }
