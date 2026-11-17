from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import compare, dashboard, discovery, health, recommendations, risk
from app.core.config import settings

app = FastAPI(title="Creator Intelligence Platform API", version="0.4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(dashboard.router)
app.include_router(discovery.router)
app.include_router(recommendations.router)
app.include_router(compare.router)
app.include_router(risk.router)