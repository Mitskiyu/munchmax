package auth

import (
	"errors"
	"fmt"
	"net/mail"
)

var ErrValidation = errors.New("validation failed")

func ValidEmail(email string) error {
	if len(email) > 255 {
		return fmt.Errorf("email too long: %w", ErrValidation)
	}

	if _, err := mail.ParseAddress(email); err != nil {
		return fmt.Errorf("email invalid: %w", ErrValidation)
	}

	return nil
}

func ValidPassword(password string) error {
	if len(password) < 8 {
		return fmt.Errorf("password too short: %w", ErrValidation)
	}

	if len(password) > 64 {
		return fmt.Errorf("password too long: %w", ErrValidation)
	}

	return nil
}
func ValidUsername(username string) error {
	if len(username) < 3 {
		return fmt.Errorf("username too short: %w", ErrValidation)
	}

	if len(username) > 32 {
		return fmt.Errorf("username too long: %w", ErrValidation)
	}

	for _, c := range username {
		if (c < 'A' || c > 'Z') && (c < 'a' || c > 'z') && (c < '0' || c > '9') {
			return fmt.Errorf("username invalid: %w", ErrValidation)
		}
	}

	return nil
}
