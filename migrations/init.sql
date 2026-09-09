DROP TABLE IF EXISTS restaurants;

CREATE TABLE restaurants (
    id             text PRIMARY KEY,
    name           text NOT NULL,
    kind           text NOT NULL,

    cuisines       text[] NOT NULL DEFAULT '{}',

    street         text,
    housenumber    text,
    postcode       text,
    city           text,

    website        text,
    phone          text,
    opening_hours  text,

    lat            double precision NOT NULL,
    lon            double precision NOT NULL,
    updated_at     timestamptz NOT NULL DEFAULT now()
);