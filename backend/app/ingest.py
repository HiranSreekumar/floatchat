"""
CLI: pull real profiles from Argovis for a region/date range into Postgres.

Usage:
    python -m app.ingest --region mumbai --start 2023-06-01 --end 2023-09-30
    python -m app.ingest --all-regions --start 2023-06-01 --end 2023-09-30 --fallback-demo
"""
import argparse
import sys

from .db import init_db, upsert_profile, insert_measurements, get_conn, row_counts
from .argovis_client import fetch_profiles, normalize_profile, ArgovisError
from .geo import GAZETTEER
from . import demo_data


def ingest_box(lon_min, lat_min, lon_max, lat_max, start_date, end_date):
    raw_profiles = fetch_profiles(
        start_date=start_date,
        end_date=end_date,
    )

    # Filter real Argovis profiles locally by geographic coordinates.
    raw_profiles = [
        raw for raw in raw_profiles
        if (
            raw.get("geolocation")
            and lon_min <= raw["geolocation"]["coordinates"][0] <= lon_max
            and lat_min <= raw["geolocation"]["coordinates"][1] <= lat_max
        )
    ]

    print(f"  -> {len(raw_profiles)} profiles found inside requested region")

    with get_conn() as conn:
        n = 0

        for raw in raw_profiles:
            try:
                p = normalize_profile(raw)
            except Exception as e:
                print(f"  skipping malformed profile: {e}", file=sys.stderr)
                continue

            if not p["profile_id"] or not p["levels"]:
                continue

            upsert_profile(
                conn,
                p["profile_id"],
                p["platform_id"],
                p["lat"],
                p["lon"],
                p["date"],
                source="argo",
                is_synthetic=False,
            )

            insert_measurements(conn, p["profile_id"], p["levels"])
            n += 1

        conn.commit()

    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", help="Named region from the gazetteer, e.g. mumbai")
    ap.add_argument("--box", help="lon_min,lat_min,lon_max,lat_max")
    ap.add_argument("--all-regions", action="store_true")
    ap.add_argument("--radius-deg", type=float, default=2.0)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--fallback-demo", action="store_true")
    args = ap.parse_args()

    init_db()

    regions_to_fetch = []

    if args.all_regions:
        regions_to_fetch = list(GAZETTEER.items())

    elif args.region:
        key = args.region.lower()

        if key not in GAZETTEER:
            print(
                f"Unknown region '{args.region}'. Known: {list(GAZETTEER)}",
                file=sys.stderr,
            )
            sys.exit(1)

        regions_to_fetch = [(key, GAZETTEER[key])]

    total = 0

    try:
        if args.box:
            lon_min, lat_min, lon_max, lat_max = map(
                float,
                args.box.split(",")
            )

            total += ingest_box(
                lon_min,
                lat_min,
                lon_max,
                lat_max,
                args.start,
                args.end,
            )

        for name, (lat, lon) in regions_to_fetch:
            r = args.radius_deg

            print(
                f"Fetching {name} ({lat},{lon}) +/- {r} deg, "
                f"{args.start}..{args.end} ..."
            )

            n = ingest_box(
                lon - r,
                lat - r,
                lon + r,
                lat + r,
                args.start,
                args.end,
            )

            print(f"  -> {n} profiles ingested")
            total += n

    except ArgovisError as e:
        print(f"Argovis fetch failed: {e}", file=sys.stderr)

        if args.fallback_demo:
            print("Falling back to offline demo dataset...")
            demo_data.generate_and_load()
        else:
            sys.exit(1)

    print(
        f"Done. Ingested {total} real profiles. "
        f"DB now has: {row_counts()}"
    )


if __name__ == "__main__":
    main()