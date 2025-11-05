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
