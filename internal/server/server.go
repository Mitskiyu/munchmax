package server

import (
	"net/http"
	"time"
)

func New(addr string, h Handlers) *http.Server {
	return &http.Server{
		Addr:              addr,
		Handler:           routes(h),
		ReadTimeout:       5 * time.Second,
		WriteTimeout:      10 * time.Second,
		ReadHeaderTimeout: 2 * time.Second,
		IdleTimeout:       120 * time.Second,
		MaxHeaderBytes:    1 << 20,
	}
}
