package auth

type Service interface {
	SignUp(email, password, username string) error
}

type service struct{}

func NewService() Service {
	return &service{}
}

func (s *service) SignUp(email, password, username string) error {
	if err := ValidEmail(email); err != nil {
		return err
	}

	if err := ValidPassword(password); err != nil {
		return err
	}

	if err := ValidUsername(username); err != nil {
		return err
	}

	return nil // TODO: hash, store
}
