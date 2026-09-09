package database

import (
	"context"
	"fmt"

	"github.com/jackc/pgx/v5/pgxpool"
)

func Connect(user, password, host, port, name string) (*pgxpool.Pool, error) {
	connStr := fmt.Sprintf("postgres://%s:%s@%s:%s/%s?sslmode=disable",
		user, password, host, port, name)

	db, err := pgxpool.New(context.Background(), connStr)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to pg: %w", err)
	}

	return db, nil
}

func Ping(db *pgxpool.Pool) error {
	if err := db.Ping(context.Background()); err != nil {
		return fmt.Errorf("failed to ping pg: %w", err)
	}

	return nil
}
