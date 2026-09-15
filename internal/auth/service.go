package auth

import "log"

type Service interface {
	SignUp(email, password, username string) error
}

type service struct{}

func NewService() Service {
	return &service{}
}

func (s *service) SignUp(email, password, username string) error {
	log.Println("signup request received:", email, username)
	return nil // TODO: validate, hash, store
}
