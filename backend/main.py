from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os

from database import engine, Base
import models  # noqa: F401 — registers all models

from routers import auth, groups, meetings, availability, records

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Meeting Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(groups.router)
app.include_router(meetings.router)
app.include_router(availability.router)
app.include_router(records.router)

# Serve frontend
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/static", StaticFiles(directory=os.path.join(frontend_dir, "static")), name="static")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str):
        # Try to serve a specific HTML file, else fall back to index.html
        target = os.path.join(frontend_dir, full_path)
        if os.path.isfile(target):
            return FileResponse(target)
        return FileResponse(os.path.join(frontend_dir, "index.html"))
