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
    params = {
       "startDate": f"{start_date}T00:00:00Z",
       "endDate": f"{end_date}T23:59:59Z",
       "data": data_vars,
}
    if box:
        # Convert two-corner box into the polygon format expected by /argo.
        lon1, lat1 = box[0]
        lon2, lat2 = box[1]
        params["polygon"] = _fmt([
             (lon1, lat1),
             (lon2, lat1),
             (lon2, lat2),
             (lon1, lat2),
             (lon1, lat1),
         ])
    elif polygon:
        params["polygon"] = _fmt(polygon)
    if pres_range:
        params["presRange"] = f"{pres_range[0]},{pres_range[1]}"

    url = f"{ARGOVIS_BASE_URL}/argo"
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

    data = raw.get("data", [])
    data_info = raw.get("data_info", [])

    # Argovis returns data arrays in the order specified by data_info.
    variable_names = []
    if data_info and len(data_info) > 0:
        variable_names = data_info[0]

    values = {}
    for name, array in zip(variable_names, data):
        values[name] = array

    temperatures = values.get("temperature", [])
    pressures = values.get("pressure", [])
    salinities = values.get("salinity", [])

    levels = []

    for pres, temp, psal in zip(pressures, temperatures, salinities):
        if pres is not None:
            levels.append((pres, temp, psal))

    platform_id = raw.get("platform_id") or raw.get("platform")

    if not platform_id:
        metadata = raw.get("metadata", [])
        if metadata:
            platform_id = str(metadata[0]).split("_")[0]

    return {
        "profile_id": raw.get("_id"),
        "platform_id": str(platform_id or "unknown"),
        "lat": lat,
        "lon": lon,
        "date": (raw.get("timestamp") or "")[:10],
        "levels": levels,
    }