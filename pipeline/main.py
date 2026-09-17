import json
import os
import time
from pathlib import Path

import duckdb
from dotenv import load_dotenv
from tavily import TavilyClient
from tavily.errors import (
    BadRequestError,
    ForbiddenError,
    InvalidAPIKeyError,
    MissingAPIKeyError,
    UsageLimitExceededError,
)


def main():
    load_dotenv()
    run()


def run():
    fsq_token = os.environ["FSQ_TOKEN"]
    tavily_key = os.environ["TAVILY_KEY"]

    data_dir = Path(__file__).resolve().parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    district = ["Sham Shui Po District"]
    locality_zh = {
        "mei foo": "美孚",
        "lai chi kok": "荔枝角",
        "cheung sha wan": "長沙灣",
        "sham shui po": "深水埗",
        "shek kip mei": "石硤尾",
        "yau yat tsuen": "又一村",
        "tai wo ping": "大窩坪",
        "stonecutters island": "昂船洲",
    }

    with duckdb.connect(data_dir / "hk.db") as con:
        parquet = data_dir / "hk.parquet"
        if not parquet.exists():
            save_places(con, fsq_token)
            filter_restaurants(con, district, parquet)
            con.sql(f"""
                SELECT COUNT(*) AS n, district
                FROM '{parquet}'
                GROUP BY district
                ORDER BY n DESC;
            """).show()

        cache_dir = data_dir / "cache"
        cache_dir.mkdir(exist_ok=True)

        limit = None
        rows = con.execute(f"""
            SELECT fsq_place_id, name, locality, district_zh
            FROM '{parquet}'
        """).fetchall()
        if limit:
            rows = rows[:limit]

        client = TavilyClient(tavily_key)
        fetch_sources(cache_dir, client, rows, locality_zh)


def save_places(con, token):
    con.execute(f"""
        INSTALL httpfs;
        LOAD httpfs;

        CREATE SECRET iceberg_secret (
            TYPE ICEBERG,
            TOKEN '{token}'
        );

        ATTACH 'places' AS fsq (
            TYPE iceberg,
            SECRET iceberg_secret,
            ENDPOINT 'https://catalog.h3-hub.foursquare.com/iceberg'
        );
    """)

    con.execute("""
        INSTALL spatial;
        LOAD spatial;

        CREATE OR REPLACE TABLE districts AS
        SELECT *
        FROM ST_Read('https://www.had.gov.hk/psi/hong-kong-administrative-boundaries/hksar_18_district_boundary.json');
    """)

    # bbox filters before download
    long_min, lat_min, long_max, lat_max = con.execute("""
        SELECT
            ST_XMin(g),
            ST_YMin(g),
            ST_XMax(g),
            ST_YMax(g)
        FROM (
            SELECT ST_Extent(ST_Union_Agg(geom)) AS g
            FROM districts
        );
    """).fetchone()

    con.execute(
        """
        CREATE OR REPLACE TABLE places AS
        SELECT * EXCLUDE(geom)
        FROM fsq.datasets.places_os AS p
        WHERE
            p.longitude BETWEEN $1 AND $2
            AND p.latitude BETWEEN $3 AND $4
            AND ST_Within(
                ST_Point(p.longitude, p.latitude),
                (SELECT ST_Union_Agg(geom) FROM districts)
            );
        """,
        [long_min, long_max, lat_min, lat_max],
    )


def filter_restaurants(con, districts, out):
    con.execute(
        """
        COPY (
            SELECT
                p.*,
                d.district AS district,
                d."地區" AS district_zh
            FROM places AS p
            JOIN districts AS d
                ON ST_Within(ST_Point(p.longitude, p.latitude), d.geom)
            WHERE list_contains($1, d.district)
            AND len(list_filter(
                fsq_category_labels,
                lambda x : starts_with(x, 'Dining and Drinking')
                    AND split_part(x, ' > ', 2) NOT IN (
                        'Bar', 'Winery', 'Vineyard', 'Brewery', 'Distillery'
                    )
            )) > 0
            AND NOT EXISTS (
                SELECT 1
                FROM places c
                WHERE c.name = p.name
                GROUP BY name
                HAVING COUNT(*) >= 10
            )
            AND date_closed IS NULL
            AND unresolved_flags IS NULL
            ) TO $2;
        """,
        [districts, str(out)],
    )


def fetch_sources(dir, client, rows, transl):
    for id, name, local, dist in rows:
        save = dir / f"{id}.json"
        if save.exists():
            continue

        if local is not None:
            local_clean = local.strip().strip(",").lower()
            if local_clean in transl:
                local_clean = transl[local_clean]
            elif any(
                "\u4e00" <= c <= "\u9fff" or "\u3400" <= c <= "\u4dbf"
                for c in local_clean
            ) and not local_clean.endswith("區"):
                pass  # keep cjk
            else:
                local_clean = dist
        else:
            local_clean = dist

        query = f"{name} {local_clean}"

        resp = None
        for attempt in range(5):
            try:
                resp = client.search(
                    query=query,
                    include_answer="advanced",
                    search_depth="basic",
                    max_results=20,
                    include_published_date=True,
                    include_images=True,
                    include_image_descriptions=True,
                    include_usage=True,
                    chunks_per_source=5,
                )
                break

            except (
                UsageLimitExceededError,
                ForbiddenError,
                BadRequestError,
                InvalidAPIKeyError,
                MissingAPIKeyError,
            ):
                raise

            except Exception as e:
                if attempt == 4:
                    print(f"failed to get sources for {id}: {e}")
                    resp = None
                    break
                time.sleep(2**attempt)

        if resp is None:
            continue

        with open(save, "w", encoding="utf-8") as f:
            json.dump(
                {"query": query, "response": resp}, f, ensure_ascii=False, indent=2
            )

        print(f"wrote: {save}")


if __name__ == "__main__":
    main()
