-- name: ListRestaurants :many
SELECT id, name, kind, cuisines, street, housenumber, 
    postcode, city, website, phone, opening_hours
FROM restaurants
WHERE id > sqlc.arg(cursor)
ORDER BY id
LIMIT sqlc.arg(row_limit);
