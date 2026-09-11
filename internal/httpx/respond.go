package httpx

import (
	"encoding/json"
	"log"
	"net/http"
)

type httpxError struct {
	Code string `json:"code"`
	Msg  string `json:"message"`
}

func Error(w http.ResponseWriter, code, msg string, statusCode int) {
	h := w.Header()
	h.Del("Content-Length")
	h.Set("X-Content-Type-Options", "nosniff")
	Write(w, httpxError{code, msg}, statusCode)
}

func Write(w http.ResponseWriter, v any, statusCode int) {
	h := w.Header()
	h.Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	if err := json.NewEncoder(w).Encode(v); err != nil {
		log.Printf("failed to encode: %v", err)
	}
}
