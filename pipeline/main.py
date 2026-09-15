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

    with duckdb.connect() as con:
        attach_places(con, fsq_token)

        hk = (22.1367222, 22.5683333, 113.8171111, 114.5024444)  # lat, long
        parquet = save_places(con, hk, f"{data_dir}/hk")

        kowloon = [
            "Kowloon City District",
            "Kwun Tong District",
            "Sham Shui Po District",
            "Wong Tai Sin District",
            "Yau Tsim Mong District",
        ]

        filter_district(con, kowloon, parquet)
        # fetch_sources(con, client)


def attach_places(con, token):
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


def save_places(con, bbox, out):
    lat_min, lat_max, lng_min, lng_max = bbox
    con.execute(
        """
        CREATE OR REPLACE TABLE places AS SELECT *
        FROM fsq.datasets.places_os
        WHERE 
            latitude BETWEEN $1 AND $2
            AND longitude BETWEEN $3 AND $4
        """,
        [lat_min, lat_max, lng_min, lng_max],
    )

    path = f"{out}.parquet"
    con.execute(f"""
        COPY (
            SELECT * EXCLUDE(geom)
            FROM places
            WHERE len(list_filter(
                fsq_category_labels,
                lambda x : starts_with(x, 'Dining and Drinking')
                AND split_part(x, ' > ', 2) NOT IN (
                    'Bar', 'Winery', 'Vineyard', 'Brewery', 'Distillery'
                )
            )) > 0
            AND date_closed IS NULL
            AND unresolved_flags IS NULL
        ) TO '{path}';
        """)

    return path


def filter_district(con, district, parquet):
    con.execute("""
        INSTALL spatial;
        LOAD spatial;

        CREATE OR REPLACE TABLE districts AS SELECT *
        FROM ST_Read('https://www.had.gov.hk/psi/hong-kong-administrative-boundaries/hksar_18_district_boundary.json');
    """)

    con.sql(
        f"""
        SELECT d.district, COUNT(*) AS num_places
        FROM '{parquet}' p JOIN districts d
            ON ST_Within(ST_Point(p.longitude, p.latitude), d.geom)
        WHERE list_contains($1, d.district)
        GROUP BY d.district
        ORDER BY num_places DESC;
        """,
        params=[district],
    ).show()


# def fetch_sources(con, client):

if __name__ == "__main__":
    main()
