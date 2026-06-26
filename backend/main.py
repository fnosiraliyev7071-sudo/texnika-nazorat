"""
Texnika Nazorat Tizimi — FastAPI Backend
"""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import os

from database import init_db
from routers.all_routers import (
    auth_router, users_router, eq_router,
    assign_router, report_router, penalty_router,
    search_router, audit_router
)

# ── App ──
app = FastAPI(
    title="Texnika Nazorat Tizimi",
    description="Qurilish va yo'l qurilishi texnikalarini boshqarish tizimi",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routerlar ──
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(eq_router)
app.include_router(assign_router)
app.include_router(report_router)
app.include_router(penalty_router)
app.include_router(search_router)
app.include_router(audit_router)

# ── Static fayllar ──
if os.path.exists("frontend"):
    app.mount("/static", StaticFiles(directory="frontend"), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def root():
        with open("frontend/index.html", "r", encoding="utf-8") as f:
            return f.read()

# ── Startup ──
@app.on_event("startup")
async def startup():
    init_db()
    print("✅ Texnika Nazorat Tizimi ishga tushdi!")
    print("📖 API hujjatlar: http://localhost:8000/docs")

# ── Health check ──
@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("ENV", "production") == "development",
    )
