"""
Offline demo dataset generator — scientifically realistic ARGO-style
profiles for the Arabian Sea and Bay of Bengal, flagged is_synthetic=True.
"""
import random
from datetime import date, timedelta

from .geo import GAZETTEER
from .db import get_conn, upsert_profile, insert_measurements

REGIONS = [
    ("mumbai", "arabian_sea"), ("goa", "arabian_sea"), ("kochi", "arabian_sea"),
    ("mangalore", "arabian_sea"), ("lakshadweep", "arabian_sea"), ("gujarat coast", "arabian_sea"),
    ("chennai", "bay_of_bengal"), ("visakhapatnam", "bay_of_bengal"), ("kolkata", "bay_of_bengal"),
    ("paradip", "bay_of_bengal"), ("andaman islands", "bay_of_bengal"), ("puducherry", "bay_of_bengal"),
]

PRESSURE_LEVELS = [0, 5, 10, 20, 30, 50, 75, 100, 150, 200, 300, 400, 500, 700, 1000, 1500, 2000]


def _is_monsoon(d):
    return d.month in (6, 7, 8, 9)


def _surface_temp(basin, d):
    base = 28.5 if basin == "arabian_sea" else 29.0
    if d.month in (4, 5):
        base += 1.2
    elif d.month in (12, 1, 2):
        base -= 1.5
    return base + random.uniform(-0.4, 0.4)


def _surface_salinity(basin, d):
    if basin == "arabian_sea":
        base = 36.2
        if _is_monsoon(d):
            base -= 0.5
    else:
        base = 33.4
        if _is_monsoon(d):
            base -= 1.8
    return base + random.uniform(-0.2, 0.2)


def _profile_curve(basin, d):
    sst = _surface_temp(basin, d)
    sss = _surface_salinity(basin, d)
    mixed_layer_depth = 40 if not _is_monsoon(d) else 25

    levels = []
    for p in PRESSURE_LEVELS:
        if p <= mixed_layer_depth:
            temp = sst - random.uniform(0, 0.3)
            sal = sss + random.uniform(-0.05, 0.05)
        elif p <= 250:
            frac = (p - mixed_layer_depth) / (250 - mixed_layer_depth)
            temp = sst - frac * (sst - 15.5)
            if basin == "bay_of_bengal":
                sal = sss + frac * (34.6 - sss)
            else:
                sal = sss - frac * (sss - 35.3)
        elif p <= 1000:
            frac = (p - 250) / (1000 - 250)
            temp = 15.5 - frac * (15.5 - 7.0)
            sal = (34.6 if basin == "bay_of_bengal" else 35.3) - frac * 0.4
        else:
            frac = min((p - 1000) / 1000, 1.0)
            temp = 7.0 - frac * 2.5
            sal = 34.7 + random.uniform(-0.05, 0.05)
        temp = round(temp + random.uniform(-0.15, 0.15), 3)
        sal = round(sal + random.uniform(-0.03, 0.03), 3)
        levels.append((float(p), temp, sal))
    return levels


def generate_and_load(num_years=3, floats_per_region_per_month=2, seed=42):
    random.seed(seed)
    today = date.today()
    start = today.replace(year=today.year - num_years)

    with get_conn() as conn:
        platform_counter = 9000
        for region_name, basin in REGIONS:
            base_lat, base_lon = GAZETTEER[region_name]
            platform_counter += 1
            platform_id = f"29{platform_counter}"

            d = start
            month_seen = set()
            while d <= today:
                key = (d.year, d.month)
                if key not in month_seen:
                    month_seen.add(key)
                    for _ in range(floats_per_region_per_month):
                        jitter_lat = base_lat + random.uniform(-1.3, 1.3)
                        jitter_lon = base_lon + random.uniform(-1.3, 1.3)
                        pdate = d + timedelta(days=random.randint(0, 27))
                        if pdate > today:
                            pdate = today
                        profile_id = f"demo_{platform_id}_{pdate.isoformat()}_{random.randint(1000,9999)}"
                        upsert_profile(
                            conn, profile_id, platform_id,
                            round(jitter_lat, 4), round(jitter_lon, 4),
                            pdate.isoformat(), source="demo", is_synthetic=True,
                        )
                        levels = _profile_curve(basin, pdate)
                        insert_measurements(conn, profile_id, levels)
                d += timedelta(days=5)
        conn.commit()


if __name__ == "__main__":
    from .db import init_db, row_counts
    init_db()
    generate_and_load()
    print("Loaded demo dataset:", row_counts())
