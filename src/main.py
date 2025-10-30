from fastapi import FastAPI, Depends
import db_models
from db import engine

from routes import user
from auth import require_basic_auth

app = FastAPI(title="python api", dependencies=[Depends(require_basic_auth)])

db_models.Base.metadata.create_all(bind=engine)

app.include_router(user.router)


@app.get("/")
def root():
    return {"message": "python api", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}
