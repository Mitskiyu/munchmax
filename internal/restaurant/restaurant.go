package restaurant

import "uuid"

type restaurant struct {
	ID           uuid.UUID `json:"id"`
	Name         string    `json:"name"`
	Kind         string    `json:"kind"`
	Cuisines     []string  `json:"cuisines"`
	Street       string    `json:"street"`
	Housenumber  string    `json:"housenumber"`
	Postcode     string    `json:"postcode"`
	City         string    `json:"city"`
	Website      string    `json:"website"`
	Phone        string    `json:"phone"`
	OpeningHours string    `json:"opening_hours"`
}
