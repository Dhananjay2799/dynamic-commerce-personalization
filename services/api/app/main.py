from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine
from app.core.redis import redis_client


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Real-time e-commerce personalization and recommendation API.",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "service": settings.app_name,
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health():
    postgres_status = "unhealthy"
    redis_status = "unhealthy"

    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

        postgres_status = "healthy"
    except Exception:
        pass

    try:
        await redis_client.ping()
        redis_status = "healthy"
    except Exception:
        pass

    overall_status = (
        "healthy"
        if postgres_status == "healthy"
        and redis_status == "healthy"
        else "degraded"
    )

    return {
        "status": overall_status,
        "services": {
            "api": "healthy",
            "postgres": postgres_status,
            "redis": redis_status,
        },
    }