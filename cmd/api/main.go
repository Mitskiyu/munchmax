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
)

func main() {
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

	s := &http.Server{
		Addr: addr,
		Handler: http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			_, _ = w.Write([]byte("Munchmax!"))
		}),
		ReadTimeout:       5 * time.Second,
		WriteTimeout:      10 * time.Second,
		ReadHeaderTimeout: 2 * time.Second,
		IdleTimeout:       120 * time.Second,
		MaxHeaderBytes:    1 << 20,
	}

	errs := make(chan error, 1)
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	go func() {
		if err := s.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			errs <- fmt.Errorf("server shut down: %v", err)
		}
	}()

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
