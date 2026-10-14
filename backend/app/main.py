"""FastAPI application entry point."""
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.database import engine
from app.models.schema import Base

app = FastAPI(
    title="NM-HireX",
    version="1.0.0",
)

# ============================================================
# CORS
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "https://nm-hire-x.vercel.app",
        "https://nm-hire-x-omega.vercel.app",
        "https://nm-hire-xv-2.vercel.app",
        "https://nm-hire-xv-2-bc2a.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# API ROUTES
# ============================================================
app.include_router(router)

# ============================================================
# HEALTH CHECK
# ============================================================
@app.get("/health")
def health():
    """Simple service health response."""
    return {"status": "ok"}

# ============================================================
# FRONTEND STATIC
# ============================================================
_ui_dir = Path(__file__).resolve().parents[2] / "frontend-static"
if _ui_dir.is_dir():
    app.mount("/ui", StaticFiles(directory=str(_ui_dir), html=True), name="static-ui")