import os
import duckdb
from dotenv import load_dotenv


def main():
    load_dotenv()
    run()


def run():
    fsq_token = os.environ["FSQ_TOKEN"]

    with duckdb.connect() as con:
        attach_places(con, fsq_token)


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


if __name__ == "__main__":
    main()
