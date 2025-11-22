from fastapi import FastAPI, Request, status
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from .routes import auth, user, score
from .utils.custom_exceptions import AuthenticationException

app = FastAPI(title="python api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",  # angular dev
        "http://localhost:3000",  # local frontend
        "http://localhost:5173",  # Vite dev
        "https://clicktuki.vercel.app",  # Vercel frontend
        "https://clicktuki.com",  # production
        "https://*.vercel.app",  # allow all Vercel preview deployments
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from fastapi.openapi.utils import get_openapi


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="python api",
        version="1.0.0",
        description="API with JWT authentication.",
        routes=app.routes,
    )

    if "components" not in openapi_schema:
        openapi_schema["components"] = {}

    if "securitySchemes" not in openapi_schema["components"]:
        openapi_schema["components"]["securitySchemes"] = {}

    openapi_schema["components"]["securitySchemes"]["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }

    # Lista de endpoints públicos que NO requieren autenticación
    public_endpoints = [
        ("/auth/register", "post"),
        ("/auth/login", "post"),
        ("/auth/refresh", "post"),
        ("/", "get"),
        ("/health", "get"),
        ("/scores/leaderboard", "get"),
    ]

    for path, path_item in openapi_schema["paths"].items():
        for method, operation in path_item.items():
            # Solo agregar seguridad si NO es un endpoint público
            is_public = any(
                path == pub_path and method == pub_method
                for pub_path, pub_method in public_endpoints
            )

            if not is_public:
                operation["security"] = [{"BearerAuth": []}]
            else:
                operation["security"] = []

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# Note: Tables are managed by Alembic migrations, not created here
# Run: alembic upgrade head

app.include_router(user.router)
app.include_router(auth.router)
app.include_router(score.router)


# Global exception handlers
@app.exception_handler(AuthenticationException)
async def authentication_exception_handler(
    request: Request, exc: AuthenticationException
):
    """Handle authentication exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors."""
    import logging

    logger = logging.getLogger(__name__)
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


@app.get("/")
def root():
    """Root endpoint."""
    return {"message": "python api", "docs": "/docs"}


@app.get("/health")
def health():
    """Health check endpoint with database connectivity test."""
    from .database import test_connection

    db_status = "connected" if test_connection() else "disconnected"
    overall_status = "healthy" if db_status == "connected" else "unhealthy"

    return {"status": overall_status, "database": db_status, "api": "ok"}
