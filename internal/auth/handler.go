package auth

import (
	"encoding/json"
	"errors"
	"log"
	"net/http"
)

type SignUpReq struct {
	Email    string `json:"email"`
	Password string `json:"password"`
	Username string `json:"username"`
}

type Handler struct {
	service Service
}

func NewHandler(service Service) *Handler {
	return &Handler{
		service: service,
	}
}

func (h *Handler) SignUp(w http.ResponseWriter, r *http.Request) {
	var req SignUpReq
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "INVALID_REQUEST", http.StatusBadRequest)
		return
	}

	if err := h.service.SignUp(req.Email, req.Password, req.Username); err != nil {
		if errors.Is(err, ErrValidation) {
			http.Error(w, "INVALID_REQUEST", http.StatusBadRequest)
			return
		}

		log.Printf("%v at %s", err, r.URL.Path)
		http.Error(w, "INTERNAL_SERVER_ERROR", http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusCreated)
}
