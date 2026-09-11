package server

import (
	"net/http"

	"munchmax/internal/restaurant"
)

type Handlers struct {
	Restaurant *restaurant.Handler
}

func routes(h Handlers) http.Handler {
	mux := http.NewServeMux()

	mux.HandleFunc("GET /health", func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write([]byte("OK"))
	})

	mux.HandleFunc("GET /restaurants", h.Restaurant.List)

	return mux
}
