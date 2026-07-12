package evaltask

import (
	"errors"
	"fmt"
	"strconv"
)

// ParsePositiveInt parses s as a positive integer.
func ParsePositiveInt(s string) (int, error) {
	n, err := strconv.Atoi(s)
	if err != nil {
		return 0, fmt.Errorf("parse positive int %q: %w", s, err)
	}
	if n <= 0 {
		return 0, fmt.Errorf("parse positive int %q: %w", s, errors.New("must be positive"))
	}
	return n, nil
}
