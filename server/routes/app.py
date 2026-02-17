import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from server.routes.audit import router as audit_router
from server.routes.health import router as health_router
from server.routes.ocr import router as ocr_router
from server.services import DBService

@asynccontextmanager
async def lifespan(app: FastAPI):
    DBService().init_db()
    yield

app = FastAPI(
    title="Transparent-Audit API",
    version="0.1.0",
    lifespan=lifespan,
)

# Mount static files
data_raw_path = Path(__file__).resolve().parents[2] / "data" / "raw"
data_raw_path.mkdir(parents=True, exist_ok=True)
app.mount("/data/raw", StaticFiles(directory=str(data_raw_path)), name="raw_data")

# CORS configuration
frontend_url = os.getenv("FRONTEND_URL", "*")
origins = [url.strip() for url in frontend_url.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(ocr_router)
app.include_router(audit_router)
