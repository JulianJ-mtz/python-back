"""FastAPI application entry point."""
from fastapi import FastAPI

from .database import engine
from .models import Base
from .routes import auth, user

app = FastAPI(title="python api")

# Create tables (en desarrollo - en producción usar migraciones)
Base.metadata.create_all(bind=engine)

app.include_router(user.router)
app.include_router(auth.router)


@app.get("/")
def root():
    """Root endpoint."""
    return {"message": "python api", "docs": "/docs"}


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}

