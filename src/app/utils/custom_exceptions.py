from fastapi import HTTPException, status


class AuthenticationException(HTTPException):
    """Base authentication exception."""

    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class TokenExpiredException(AuthenticationException):
    """Token has expired."""

    def __init__(self):
        super().__init__(detail="Token has expired")


class InvalidTokenException(AuthenticationException):
    """Invalid token."""

    def __init__(self, detail: str = "Invalid token"):
        super().__init__(detail=detail)


class UserNotFoundException(AuthenticationException):
    """User not found."""

    def __init__(self):
        super().__init__(detail="User not found")


class InvalidCredentialsException(AuthenticationException):
    """Invalid credentials."""

    def __init__(self):
        super().__init__(detail="Invalid credentials")


class ResourceNotFoundException(HTTPException):
    """Resource not found."""

    def __init__(self, resource: str = "Resource"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} not found",
        )


class DuplicateResourceException(HTTPException):
    """Duplicate resource."""

    def __init__(self, detail: str = "Resource already exists"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )


class InvalidInputScoreException(HTTPException):
    """Invalid mode_value for the provided mode."""

    def __init__(self, mode, mode_value, valid_values):
        mode_name = getattr(mode, "value", str(mode))
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid mode_value {mode_value} for {mode_name} mode. "
                f"Valid values: {sorted(valid_values)}"
            ),
        )


class InvalidScoreMetricsException(HTTPException):
    """Invalid score metrics provided."""

    def __init__(self, detail: str = "Invalid score metrics provided"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )


class DatabaseOperationException(HTTPException):
    """Database operation failed."""

    def __init__(self, detail: str = "Database operation failed"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        )


class TooManyRequestsException(HTTPException):
    """Too many requests were submitted within a limited window."""

    def __init__(self, detail: str = "Too many requests", retry_after: int = 60):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers={"Retry-After": str(retry_after)},
        )


class PasswordTooLongException(HTTPException):
    """Password exceeds bcrypt byte length limit."""

    def __init__(self, max_bytes: int):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Password is too long. "
                f"Ensure it is at most {max_bytes} bytes when encoded as UTF-8."
            ),
        )
