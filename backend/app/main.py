from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base
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

    # Pre-index existing documents with extracted text into the in-memory vector store
    try:
        from app.core.database import SessionLocal
        from app.models.document import Document
        from app.ai.vector_store import vector_store
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
