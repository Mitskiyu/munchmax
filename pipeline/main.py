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
    os.makedirs(data_dir, exist_ok=True)

    kowloon = [
        "Kowloon City District",
        "Kwun Tong District",
        "Sham Shui Po District",
        "Wong Tai Sin District",
        "Yau Tsim Mong District",
    ]

    with duckdb.connect() as con:
        attach_places(con, fsq_token)
        load_districts(con)
        parquet = save_places(con, f"{data_dir}/hk")
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


def load_districts(con):
    con.execute("""
        INSTALL spatial;
        LOAD spatial;

        CREATE OR REPLACE TABLE districts AS SELECT *
        FROM ST_Read('https://www.had.gov.hk/psi/hong-kong-administrative-boundaries/hksar_18_district_boundary.json');
    """)


def save_places(con, out):
    long_min, lat_min, long_max, lat_max = con.execute("""
        SELECT ST_XMin(g), ST_YMin(g), ST_XMax(g), ST_YMax(g)
        FROM (SELECT ST_Extent(ST_Union_Agg(geom)) AS g FROM districts);
    """).fetchone()

    con.execute(
        """
        CREATE OR REPLACE TABLE places AS SELECT *
        FROM fsq.datasets.places_os p
        WHERE
            longitude BETWEEN $1 AND $2
            AND latitude BETWEEN $3 and $4
            AND ST_Within(ST_Point(p.longitude, p.latitude), (SELECT ST_Union_Agg(geom) FROM districts));
        """,
        [long_min, long_max, lat_min, lat_max],
    )

    path = f"{out}.parquet"
    con.execute(f"""
        COPY (
            SELECT * FROM places
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
