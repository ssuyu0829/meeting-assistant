from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError
import logging
import os
from pathlib import Path

from database import engine, Base
import models  # noqa: F401 — registers all models

from routers import auth, groups, meetings, availability, records

# Create tables
Base.metadata.create_all(bind=engine)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="Meeting Assistant")

# 前後端同源，所以預設不開放跨來源；要從別的網域呼叫就設 ALLOWED_ORIGINS（逗號分隔）
allowed_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
if allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )


@app.get("/healthz", include_in_schema=False)
def healthz():
    return {"ok": True}


@app.exception_handler(IntegrityError)
def integrity_error_handler(request: Request, exc: IntegrityError):
    """撞到唯一鍵（例如同時送出兩次）本來會變成 500，前端只看到 Request failed。"""
    logging.getLogger(__name__).warning("IntegrityError on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=409, content={"detail": "資料已存在或衝突，請重新載入後再試"})

app.include_router(auth.router)
app.include_router(groups.router)
app.include_router(meetings.router)
app.include_router(availability.router)
app.include_router(records.router)

# Serve frontend
frontend_dir = (Path(__file__).resolve().parent / ".." / "frontend").resolve()
if frontend_dir.is_dir():
    app.mount("/static", StaticFiles(directory=str(frontend_dir / "static")), name="static")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str):
        # 只回 frontend/ 底下的檔案。少了這道檢查，「/%2e%2e/backend/.env」這種路徑
        # 會把 .env（含 SECRET_KEY 與資料庫連線字串）當靜態檔送出去。
        index = frontend_dir / "index.html"
        try:
            target = (frontend_dir / full_path).resolve()
        except (OSError, ValueError):
            return FileResponse(index)
        if target.is_file() and frontend_dir in target.parents:
            return FileResponse(target)
        return FileResponse(index)
