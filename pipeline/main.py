import os

import httpx
import psycopg
from dotenv import load_dotenv

load_dotenv()

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

QUERY = """
[out:json][timeout:90];
area["name"="Den Haag"]["admin_level"=8]->.city;
nwr["amenity"~"^(restaurant|fast_food|cafe)$"](area.city);
out center tags;
"""


def fetch():
    r = httpx.post(
        OVERPASS_URL,
        data={"data": QUERY},
        headers={"User-Agent": "munchmax/0.1 (github.com/Mitskiyu/munchmax)"},
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["elements"]


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
        tags.get("addr:street"),
        tags.get("addr:housenumber"),
        tags.get("addr:postcode"),
        tags.get("addr:city"),
        tags.get("website") or tags.get("contact:website"),
        tags.get("phone") or tags.get("contact:phone"),
        tags.get("opening_hours"),
        lat,
        lon,
    )


def store(rows):
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO restaurants (
                    id, name, kind, cuisines, street, housenumber,
                    postcode, city, website, phone, opening_hours, lat, lon
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
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
                    lon           = EXCLUDED.lon,
                    updated_at    = now()
                """,
                rows,
            )


def main():
    elements = fetch()
    rows = [r for r in map(to_row, elements) if r is not None]
    store(rows)


if __name__ == "__main__":
    main()