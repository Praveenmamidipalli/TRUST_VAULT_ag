from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.core.bootstrap import bootstrap_database_if_empty
from app.models.document import Document
from app.ai.vector_store import vector_store
from app.routes.auth import router as auth_router
from app.routes.documents import router as documents_router
from app.routes.permissions import router as permissions_router
from app.routes.audit import router as audit_router
from app.routes.admin import router as admin_router
from app.routes.ai import router as ai_router

# Ensure all models are imported so metadata binds correctly
import app.models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on application startup
    Base.metadata.create_all(bind=engine)

    # Automatically bootstrap demo users and initial documents if database is empty
    try:
        with SessionLocal() as db:
            bootstrap_database_if_empty(db)
    except Exception as e:
        print(f"[!] Warning during database bootstrap: {e}")

    # Pre-index existing documents with extracted text into the in-memory vector store
    try:
        with SessionLocal() as db:
            docs = db.query(Document).filter(Document.extracted_text.isnot(None)).all()
            for doc in docs:
                if doc.extracted_text and doc.extracted_text.strip():
                    vector_store.chunk_text(doc.id, doc.extracted_text)
    except Exception as e:
        print(f"[!] Warning during vector store warmup: {e}")

    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="TrustVault – Secure Enterprise Document Sharing & AI-Powered Document Intelligence Platform",
    lifespan=lifespan
)

# CORS Middleware (Supports local dev, production domains, and Vercel cloud deployments)
cors_origins = list(settings.CORS_ORIGINS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if "*" not in cors_origins else ["*"],
    allow_origin_regex=r"https://.*\.vercel\.app|https://.*\.tmp\.now" if "*" not in cors_origins else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 routers
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(documents_router, prefix=settings.API_V1_PREFIX)
app.include_router(permissions_router, prefix=settings.API_V1_PREFIX)
app.include_router(audit_router, prefix=settings.API_V1_PREFIX)
app.include_router(admin_router, prefix=settings.API_V1_PREFIX)
app.include_router(ai_router, prefix=settings.API_V1_PREFIX)


@app.get("/api/health", tags=["Health"])
def health_check():
    """Health check endpoint for Docker container orchestration and uptime monitoring."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION
    }


# Static files & SPA Catch-All for unified production deployment
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

frontend_dist_dirs = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")),
    "/app/frontend/dist"
]

frontend_dist = next((d for d in frontend_dist_dirs if os.path.isdir(d)), None)

if frontend_dist:
    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="API endpoint not found")
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dist, "index.html"))

