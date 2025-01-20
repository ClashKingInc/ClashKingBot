class APIUnavailableError(Exception):
    """Raised when the API is down or unavailable."""

    def __init__(self, status_code: int):
        super().__init__(f'ClashKing API is down (HTTP {status_code}).')


class NotFoundError(Exception):
    """Raised when a requested resource (e.g., ban, player, etc.) is not found."""

    def __init__(self, message: str):
        super().__init__(message)


class AuthenticationError(Exception):
    """Raised when authentication fails."""

    def __init__(self, message: str):
        super().__init__(message)
