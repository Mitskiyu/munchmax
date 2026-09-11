package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"munchmax/internal/database"
	"munchmax/internal/restaurant"
	"munchmax/internal/server"

	"github.com/joho/godotenv"
)

func main() {
	_ = godotenv.Load()
	if err := run(getenv); err != nil {
		log.Fatal(err)
	}
}

func run(getenv func(string, string) string) error {
	var (
		addr       = ":" + getenv("PORT", "8080")
		pgUser     = getenv("PG_USER", "")
		pgPassword = getenv("PG_PASSWORD", "")
		pgHost     = getenv("PG_HOST", "")
		pgPort     = getenv("PG_PORT", "")
		pgName     = getenv("PG_NAME", "")
	)

	log.Println("Connecting to postgres...")
	db, err := database.Connect(pgUser, pgPassword, pgHost, pgPort, pgName)
	if err != nil {
		return err
	}
	defer db.Close()

	if err := database.Ping(db); err != nil {
		return err
	}
	log.Printf("Connected to postgres: %s@%s:%s/%s", pgUser, pgHost, pgPort, pgName)

	q := database.New(db)
	h := server.Handlers{
		Restaurant: restaurant.NewHandler(restaurant.NewService(q)),
	}

	s := server.New(addr, h)

	errs := make(chan error, 1)
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	go func() {
		if err := s.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			errs <- fmt.Errorf("server shut down: %v", err)
		}
	}()

	log.Printf("Server listening on %s", addr)

	select {
	case <-ctx.Done():
		log.Println("Shutting down server...")
	case err := <-errs:
		return err
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	if err := s.Shutdown(ctx); err != nil {
		return fmt.Errorf("server forced to shut down: %v", err)
	}

	return nil
}

func getenv(k, dv string) string {
	v := os.Getenv(k)

	if v == "" {
		return dv
	}

	return v
}
