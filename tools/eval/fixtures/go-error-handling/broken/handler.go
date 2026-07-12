package evaltask

import "strconv"

// ParsePositiveInt parses s as a positive integer.
func ParsePositiveInt(s string) (int, error) {
	return strconv.Atoi(s)
}
