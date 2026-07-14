class CommandUsageError(Exception):
    """Raised when command-line input cannot be safely parsed."""


class ResultValidationError(TypeError):
    """Raised when a command result cannot be represented safely as JSON."""
