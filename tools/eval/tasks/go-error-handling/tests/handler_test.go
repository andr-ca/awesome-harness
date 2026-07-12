package evaltask

import "testing"

func TestParsePositiveInt_Valid(t *testing.T) {
	got, err := ParsePositiveInt("42")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got != 42 {
		t.Errorf("got %d, want 42", got)
	}
}

func TestParsePositiveInt_EdgeZero(t *testing.T) {
	if _, err := ParsePositiveInt("0"); err == nil {
		t.Error("expected error for zero, got nil")
	}
}

func TestParsePositiveInt_EdgeNegative(t *testing.T) {
	if _, err := ParsePositiveInt("-5"); err == nil {
		t.Error("expected error for negative input, got nil")
	}
}

func TestParsePositiveInt_EdgeNonNumeric(t *testing.T) {
	if _, err := ParsePositiveInt("abc"); err == nil {
		t.Error("expected error for non-numeric input, got nil")
	}
}
