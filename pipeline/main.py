import os
import time
import httpx
import psycopg
from dotenv import load_dotenv

load_dotenv()

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.osm.jp/api/interpreter",
]

HEADERS = {"User-Agent": "munchmax/0.1 (github.com/Mitskiyu/munchmax)"}
QUERY = """
[out:json][timeout:90];
area["name"="Den Haag"]["admin_level"=8]->.city;
nwr["amenity"~"^(restaurant|fast_food|cafe)$"](area.city);
out center tags;
"""


def fetch(attempts=2, backoff=10):
    for attempt in range(attempts):
        for url in OVERPASS_URLS:
            try:
                r = httpx.post(url, data={"data": QUERY}, headers=HEADERS, timeout=120)
            except httpx.HTTPError as e:
                print(f"{url} unreachable: {e}")
                continue

            if r.status_code == 429 or r.status_code >= 500:
                print(f"{url} returned HTTP {r.status_code}, trying next mirror")
                continue

            r.raise_for_status()
            data = r.json()
            return data["elements"]

        if attempt < attempts - 1:
            wait = backoff * (attempt + 1)
            print(f"all mirrors failed, waiting {wait}s before retrying")
            time.sleep(wait)

    raise RuntimeError("failed to fetch data")


def to_row(element):
    tags = element.get("tags", {})

    name = tags.get("name")
    if not name:
        return None

    if element["type"] == "node":
        lat, lon = element.get("lat"), element.get("lon")
    else:
        center = element.get("center", {})
        lat, lon = center.get("lat"), center.get("lon")

    if lat is None or lon is None:
        return None

    cuisines = [c.strip() for c in tags.get("cuisine", "").split(";") if c.strip()]

    return (
        f"{element['type']}/{element['id']}",
        name,
        tags["amenity"],
        cuisines,
        tags.get("addr:street") or "",
        tags.get("addr:housenumber") or "",
        tags.get("addr:postcode") or "",
        tags.get("addr:city") or "",
        tags.get("website") or tags.get("contact:website") or "",
        tags.get("phone") or tags.get("contact:phone") or "",
        tags.get("opening_hours") or "",
        lat,
        lon,
    )


def store(rows):
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO restaurants (
                    osm_id, name, kind, cuisines, street, housenumber,
                    postcode, city, website, phone, opening_hours, lat, lon
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (osm_id) DO UPDATE SET
                    name          = EXCLUDED.name,
                    kind          = EXCLUDED.kind,
                    cuisines      = EXCLUDED.cuisines,
                    street        = EXCLUDED.street,
                    housenumber   = EXCLUDED.housenumber,
                    postcode      = EXCLUDED.postcode,
                    city          = EXCLUDED.city,
                    website       = EXCLUDED.website,
                    phone         = EXCLUDED.phone,
                    opening_hours = EXCLUDED.opening_hours,
                    lat           = EXCLUDED.lat,
                    lon           = EXCLUDED.lon
                """,
                rows,
            )


def main():
    elements = fetch()
    rows = [r for r in map(to_row, elements) if r is not None]
    store(rows)


if __name__ == "__main__":
    main()
