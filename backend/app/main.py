"""
AurumIQ FastAPI Application Server
Problem Statement #03: Commodity Derivatives Intelligence
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database.connection import init_db
from app.api.routes import router as api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database schema is created on startup
    init_db()
    # Auto-seed benchmark historical dataset if market_data is empty
    from app.database.connection import get_db
    from app.ingestion.sample_data_loader import load_sample_data_into_db
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM market_data;")
            if cursor.fetchone()["count"] == 0:
                load_sample_data_into_db()
    except Exception as e:
        print(f"Startup data check: {e}")
    yield

app = FastAPI(
    title="AurumIQ - MCX Commodity Derivatives Intelligence API",
    description="Quantitative Relative Pricing and Arbitrage Analytics for MCX Gold Futures Contracts",
    version="1.0.0",
    lifespan=lifespan
)

import os

# CORS Middleware with configurable origins
cors_origins_raw = os.getenv("CORS_ORIGINS", "*")
if cors_origins_raw.strip() == "*":
    allow_origins = ["*"]
else:
    allow_origins = [origin.strip() for origin in cors_origins_raw.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api")

@app.get("/")
def root():
    return {
        "service": "AurumIQ API",
        "version": "1.0.0",
        "documentation": "/docs",
        "health_check": "/api/health"
    }
