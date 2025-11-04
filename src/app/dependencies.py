"""Dependencies for the application."""

from typing import Annotated

from fastapi import Depends, HTTPException, status, Request, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .utils.custom_exceptions import AuthenticationException
DbSession = Annotated[Session, Depends(get_db)]
docs_security = HTTPBearer(auto_error=False)


async def verify_api_key(
        credentials: HTTPAuthorizationCredentials = Security(docs_security),
) -> bool:
    """Verify the API key for accessing OpenAPI docs."""
    # Replace 'your-secret-api-key' with your actual API key or get it from environment variables
    if not credentials or credentials.credentials != "your-secret-api-key":
        raise AuthenticationException()
    return True


# Dependency to get the current user from the request state
async def get_current_active_user(request: Request) -> User:
    """Get the current user from the request state."""
    if not hasattr(request.state, "user") or not request.state.user:
        raise AuthenticationException()
    return request.state.user


# Type alias for the current user
CurrentUser = Depends(get_current_active_user)
