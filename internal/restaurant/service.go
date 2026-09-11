package restaurant

import (
	"context"
	"uuid"

	"munchmax/internal/database"
)

type store interface {
	ListRestaurants(ctx context.Context, arg database.ListRestaurantsParams) ([]database.ListRestaurantsRow, error)
}

type Service struct {
	store store
}

func NewService(store store) *Service {
	return &Service{
		store: store,
	}
}

func (s *Service) list(ctx context.Context, cursor uuid.UUID, limit int) ([]restaurant, error) {
	params := database.ListRestaurantsParams{
		Cursor:   cursor,
		RowLimit: int32(limit),
	}

	rests, err := s.store.ListRestaurants(ctx, params)
	if err != nil {
		return nil, err
	}

	out := make([]restaurant, 0, len(rests))
	for _, r := range rests {
		out = append(out, restaurant(r))
	}

	return out, nil
}
