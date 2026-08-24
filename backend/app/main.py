from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import get_settings
from app.database.session import init_db
from app.api import auth, vps, rdp, admin, terminal
from app.jobs.queue import start_worker, stop_worker

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    await start_worker()
    yield
    await stop_worker()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else ["https://your-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(vps.router, prefix="/api/v1")
app.include_router(rdp.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(terminal.router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.APP_VERSION}


@app.get("/")
async def root():
    return {"name": settings.APP_NAME, "version": settings.APP_VERSION}