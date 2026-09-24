"""
Gazetteer of Indian coastal / ocean reference points, used to ground
LLM geographic reasoning so it anchors to known coordinates instead of
inventing them for named places.
"""

GAZETTEER = {
    "mumbai": (19.076, 72.877),
    "goa": (15.2993, 74.1240),
    "kochi": (9.9312, 76.2673),
    "cochin": (9.9312, 76.2673),
    "mangalore": (12.9141, 74.8560),
    "kandla": (23.0333, 70.2167),
    "gujarat coast": (21.5, 70.5),
    "lakshadweep": (10.5667, 72.6417),
    "arabian sea": (15.0, 65.0),
    "gulf of kutch": (22.5, 69.5),
    "gulf of khambhat": (21.0, 72.3),
    "chennai": (13.0827, 80.2707),
    "visakhapatnam": (17.6868, 83.2185),
    "vizag": (17.6868, 83.2185),
    "kolkata": (22.5726, 88.3639),
    "paradip": (20.3167, 86.6167),
    "puducherry": (11.9416, 79.8083),
    "pondicherry": (11.9416, 79.8083),
    "andaman islands": (11.7401, 92.6586),
    "andaman sea": (10.0, 95.0),
    "bay of bengal": (15.0, 88.0),
    "kanyakumari": (8.0883, 77.5385),
    "sri lanka": (7.8731, 80.7718),
    "indian ocean": (-10.0, 75.0),
    "equator indian ocean": (0.0, 75.0),
    "maldives": (3.2028, 73.2207),
}


def gazetteer_prompt_block() -> str:
    lines = [f'- "{name}": lat={lat}, lon={lon}' for name, (lat, lon) in GAZETTEER.items()]
    return "\n".join(lines)
