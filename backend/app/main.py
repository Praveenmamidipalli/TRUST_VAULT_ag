from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base
from app.routes.auth import router as auth_router
from app.routes.documents import router as documents_router

# Ensure all models are imported so metadata binds correctly
import app.models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on application startup
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="TrustVault – Secure Enterprise Document Sharing & AI-Powered Document Intelligence Platform",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 routers
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(documents_router, prefix=settings.API_V1_PREFIX)


@app.get("/api/health", tags=["Health"])
def health_check():
    """Health check endpoint for Docker container orchestration and uptime monitoring."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION
    }
