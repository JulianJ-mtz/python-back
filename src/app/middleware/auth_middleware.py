"""Authentication middleware for FastAPI."""

import logging
from typing import Callable, Awaitable, Any

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials

from ..routes.auth import get_current_user, get_db
from ..utils.custom_exceptions import AuthenticationException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# List of paths that don't require authentication
PUBLIC_PATHS = [
    "/docs",
    "/openapi.json",
    "/",
    "/health",
    "/auth/register",
    "/auth/login",
    "/auth/refresh",
]


async def auth_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Any]]
) -> Any:
    """Middleware to authenticate requests."""

    # Skip authentication for public routes
    if request.url.path in PUBLIC_PATHS or request.url.path.startswith("/docs"):
        return await call_next(request)

    logger.info(f"Authenticating request to: {request.url.path}")

    # Get the token from the Authorization header
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        logger.warning("No Bearer token found in Authorization header")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "No authentication token provided"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header.split(" ")[1] if len(auth_header.split(" ")) > 1 else ""

    if not token:
        logger.warning("Empty token provided")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Empty token"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info("Token found, validating...")

    # Get database session
    db = next(get_db())

    try:
        # Validate token and get current user
        auth_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials=token
        )
        logger.info("Getting current user...")
        user = await get_current_user(db, auth_credentials)

        if not user:
            logger.warning("User not found for the provided token")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "User not found"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Add user to request state for use in route handlers
        request.state.user = user
        logger.info(f"User authenticated: {user.email}")

    except AuthenticationException as e:
        logger.error(f"Authentication error: {e.detail}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": e.detail},
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Unexpected error during authentication: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Authentication error"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    finally:
        db.close()

    # Continue with the request
    response = await call_next(request)
    return response
