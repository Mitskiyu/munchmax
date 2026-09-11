-- +goose Up
-- +goose StatementBegin
CREATE EXTENSION IF NOT EXISTS moddatetime;
-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
DROP EXTENSION IF EXISTS moddatetime;
-- +goose StatementEnd
