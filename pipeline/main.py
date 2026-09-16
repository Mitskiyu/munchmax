import os
import duckdb

from dotenv import load_dotenv
from pathlib import Path


def main():
    load_dotenv()
    run()


def run():
    fsq_token = os.environ["FSQ_TOKEN"]

    data_dir = Path(__file__).resolve().parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    kowloon = [
        "Kowloon City District",
        "Kwun Tong District",
        "Sham Shui Po District",
        "Wong Tai Sin District",
        "Yau Tsim Mong District",
    ]

    with duckdb.connect(data_dir / "hk.db") as con:
        save_places(con, fsq_token)
        out = filter_restaurants(con, kowloon, data_dir / "hk.parquet")
        con.sql(f"""
            SELECT COUNT(*) AS n, district
            FROM '{out}'
            GROUP BY district
            ORDER BY n DESC;
        """).show()
        # fetch_sources(con, client)


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

    return out


# def fetch_sources(con, client):

if __name__ == "__main__":
    main()
