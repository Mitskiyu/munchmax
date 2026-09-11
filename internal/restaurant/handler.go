package restaurant

import (
	"fmt"
	"log"
	"net/http"
	"net/url"
	"strconv"
	"uuid"

	"munchmax/internal/httpx"
)

const (
	defaultLimit = 20
	maxLimit     = 100
)

type Handler struct {
	service *Service
}

func NewHandler(service *Service) *Handler {
	return &Handler{
		service: service,
	}
}

func (h *Handler) List(w http.ResponseWriter, r *http.Request) {
	type res struct {
		Data []restaurant `json:"data"`
	}

	ctx := r.Context()
	params := r.URL.Query()

	cur, err := parseCursor(params)
	if err != nil {
		httpx.Error(w, "INVALID_CURSOR", err.Error(), http.StatusBadRequest)
		return
	}

	limit, err := parseLimit(params)
	if err != nil {
		httpx.Error(w, "INVALID_LIMIT", err.Error(), http.StatusBadRequest)
		return
	}

	rests, err := h.service.list(ctx, cur, limit)
	if err != nil {
		log.Printf("%v at %s", err, r.URL)
		httpx.Error(w, "INTERNAL", "internal server error", http.StatusInternalServerError)
		return
	}

	httpx.Write(w, res{Data: rests}, http.StatusOK)
}

func parseCursor(q url.Values) (uuid.UUID, error) {
	s := q.Get("after")
	if s == "" {
		return uuid.Nil(), nil
	}

	cur, err := uuid.Parse(s)
	if err != nil {
		return uuid.Nil(), fmt.Errorf("invalid cursor: %q", s)
	}

	return cur, nil
}

func parseLimit(q url.Values) (int, error) {
	s := q.Get("limit")
	if s == "" {
		return defaultLimit, nil
	}

	n, err := strconv.Atoi(s)
	if err != nil {
		return 0, fmt.Errorf("invalid limit: %q", s)
	}

	if n < 1 || n > maxLimit {
		return 0, fmt.Errorf("limit must be between 1 and %d", maxLimit)
	}

	return n, nil
}
