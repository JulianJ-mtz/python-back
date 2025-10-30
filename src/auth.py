from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import os
import secrets


security = HTTPBasic()


def require_basic_auth(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """Validate HTTP Basic credentials against env vars.

    Returns the authenticated username on success.
    """
    expected_username = os.getenv("BASIC_AUTH_USER", "admin")
    expected_password = os.getenv("BASIC_AUTH_PASS", "secret")

    username_matches = secrets.compare_digest(credentials.username, expected_username)
    password_matches = secrets.compare_digest(credentials.password, expected_password)

    if not (username_matches and password_matches):
        # RFC 7235 requires this header to prompt the browser login dialog
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username
