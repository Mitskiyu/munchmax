import asyncio
import json
import os
from pathlib import Path

import duckdb
from dotenv import load_dotenv
from openai import (
    AsyncOpenAI,
    AuthenticationError,
    BadRequestError,
)
from tavily import AsyncTavilyClient
from tavily.errors import BadRequestError as TavilyBadRequestError
from tavily.errors import (
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
    nebius_key = os.environ["NEBIUS_KEY"]

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

        source_dir = data_dir / "store" / "sources"
        source_dir.mkdir(parents=True, exist_ok=True)

        limit = None
        rows = con.execute(f"""
            SELECT fsq_place_id, name, locality, district_zh, address
            FROM '{parquet}'
        """).fetchall()
        if limit:
            rows = rows[:limit]

    profile_dir = data_dir / "store" / "profiles"
    profile_dir.mkdir(parents=True, exist_ok=True)

    tavily_client = AsyncTavilyClient(tavily_key)
    asyncio.run(fetch_sources(source_dir, tavily_client, rows, locality_zh))

    nebius_client = AsyncOpenAI(
        base_url="https://api.tokenfactory.us-central1.nebius.com/v1/",
        api_key=nebius_key,
    )

    with open("nebius/prompt.md") as f:
        prompt = f.read()
    with open("nebius/schema.json") as f:
        schema = json.load(f)

    prompt = (
        prompt + "\n\n ### Schema" + json.dumps(schema, ensure_ascii=False, indent=2)
    )

    asyncio.run(
        write_profiles(source_dir, profile_dir, nebius_client, prompt, schema, rows)
    )


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


async def fetch_source(dir, client, sem, row, transl):
    id, name, local, dist, _ = row

    save = dir / f"{id}.json"
    if save.exists():
        return

    if local is not None:
        local_clean = local.strip().strip(",").lower()
        if local_clean in transl:
            local_clean = transl[local_clean]
        elif any(
            "\u4e00" <= c <= "\u9fff" or "\u3400" <= c <= "\u4dbf" for c in local_clean
        ) and not local_clean.endswith("區"):
            pass  # keep cjk
        else:
            local_clean = dist
    else:
        local_clean = dist

    query = f"{name} {local_clean}"

    async with sem:
        resp = None
        for attempt in range(5):
            try:
                resp = await client.search(
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
                TavilyBadRequestError,
                InvalidAPIKeyError,
                MissingAPIKeyError,
            ):
                raise

            except Exception as e:
                if attempt == 4:
                    print(f"failed to get sources for {id}: {e}")
                    resp = None
                    break
                await asyncio.sleep(2**attempt)

    if resp is None:
        return

    with open(save, "w", encoding="utf-8") as f:
        json.dump(resp, f, ensure_ascii=False, indent=2)

    print(f"wrote: {save}")


async def fetch_sources(dir, client, rows, transl):
    sem = asyncio.Semaphore(10)

    tasks = [fetch_source(dir, client, sem, row, transl) for row in rows]
    await asyncio.gather(*tasks)


def build_payload(row, dir):
    id, name, locality, district, address = row

    file = dir / f"{id}.json"
    if not file.exists():
        return None

    with open(file) as f:
        data = json.load(f)

    lines = [f"NAME: {name}"]

    area = locality or district
    if area:
        lines.append(f"AREA: {area}")
    if address:
        lines.append(f"ADDRESS: {address}")

    lines.append("")
    lines.append("SOURCES:")

    n = 0
    for res in data["results"]:
        url = res.get("url") or ""
        content = res.get("content") or ""
        if not content:
            continue

        title = res.get("title") or ""
        # tavily repeats the title
        if content.startswith(f"Title: {title}"):
            content = content[len(f"Title: {title}") :].lstrip()

        n += 1
        if n > 1:
            lines.append("")
        lines.append(f"[{n}] {title}")
        lines.append(url)
        lines.append(content)
        if res.get("published_date"):
            lines.append(f"({res['published_date']})")

    if n == 0:
        return None

    return "\n".join(lines)


async def write_profile(dir, client, sem, prompt, schema, id, payload):
    save = dir / f"{id}.json"
    if save.exists():
        return

    async with sem:
        resp = None
        for attempt in range(5):
            try:
                resp = await client.chat.completions.create(
                    model="nvidia/Nemotron-3-Ultra-550b-a55b",
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": payload},
                    ],
                    max_tokens=32000,
                    temperature=0.2,
                    response_format={"type": "json_schema", "json_schema": schema},
                )
                break

            except (AuthenticationError, BadRequestError):
                raise

            except Exception as e:
                if attempt == 4:
                    print(f"failed to write profile for {id}: {e}")
                    resp = None
                    break
                await asyncio.sleep(2**attempt)

        if resp is None:
            return

        msg = resp.choices[0].message
        if msg.refusal:
            print(f"refused profile: {id}")
            return

        try:
            data = json.loads(msg.content)
        except json.JSONDecodeError:
            print(f"failed to decode json: {id}")
            return

        if resp.choices[0].finish_reason == "length":
            print(f"truncated profile: {id}")
            return

        with open(save, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"wrote: {save}")


async def write_profiles(source_dir, profile_dir, client, prompt, schema, rows):
    sem = asyncio.Semaphore(10)

    tasks = [(row[0], build_payload(row, source_dir)) for row in rows]

    await asyncio.gather(
        *[
            write_profile(profile_dir, client, sem, prompt, schema, id, payload)
            for id, payload in tasks
            if payload is not None
        ]
    )


if __name__ == "__main__":
    main()
