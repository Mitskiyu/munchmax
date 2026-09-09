-- +goose Up
-- +goose StatementBegin
CREATE TABLE restaurants (
    id            UUID PRIMARY KEY DEFAULT uuidv7(),
    osm_id        TEXT NOT NULL UNIQUE,

    name          TEXT NOT NULL,
    kind          TEXT NOT NULL,

    cuisines      TEXT[] NOT NULL DEFAULT '{}',

    street        TEXT,
    housenumber   TEXT,
    postcode      TEXT,
    city          TEXT,

    website       TEXT,
    phone         TEXT,
    opening_hours TEXT,

    lat           DOUBLE PRECISION NOT NULL,
    lon           DOUBLE PRECISION NOT NULL,

    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    modified_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER update_timestamp
BEFORE UPDATE ON restaurants
FOR EACH ROW EXECUTE FUNCTION moddatetime(modified_at);
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
DROP TABLE IF EXISTS restaurants;
-- +goose StatementEnd
