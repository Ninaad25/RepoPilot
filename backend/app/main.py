from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.repository import router as repository_router
from app.api.sandbox import router as sandbox_router
from app.database import Base, engine
from app.models import Sandbox, User


# ==================================================
# DATABASE
# ==================================================

Base.metadata.create_all(
    bind=engine
)


# ==================================================
# FASTAPI
# ==================================================

app = FastAPI(
    title="RepoPilot API",
    description="AI-powered GitHub repository demo platform",
    version="0.1.0",
)


# ==================================================
# CORS
# ==================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================================================
# ROUTES
# ==================================================

app.include_router(
    auth_router
)

app.include_router(
    repository_router
)

app.include_router(
    sandbox_router
)


# ==================================================
# ROOT
# ==================================================

@app.get("/")
def root():
    return {
        "name": "RepoPilot",
        "status": "running",
        "version": "0.1.0",
    }


# ==================================================
# HEALTH
# ==================================================

@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "service": "RepoPilot API",
    }