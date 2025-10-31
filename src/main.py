from fastapi import FastAPI

from . import db_models
from .db import engine
from .routes import user

app = FastAPI(title="python api")

db_models.Base.metadata.create_all(bind=engine)

app.include_router(user.router)


@app.get("/")
def root():
    return {"message": "python api", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}
