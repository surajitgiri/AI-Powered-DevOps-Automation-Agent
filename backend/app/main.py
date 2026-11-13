from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import app.models  # Register all database models
from app.api.v1.agents import router as agent_router
from app.api.v1.database import router as database_router
from app.core.config import settings
from app.api.v1.router import api_router

app = FastAPI(
    title="OpsPilot AI",
    description="AI Powered DevOps Automation Platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# app.include_router(
#     agent_router,
#     prefix="/api/v1/agents",
#     tags=["AI Agents"]
# )

app.include_router(
    api_router,
    prefix="/api/v1"
)

app.include_router(
    database_router,
    prefix="/api/v1",
    tags=["Database"]
)

@app.get("/")
async def root():
    return {
        "message": "Welcome to OpsPilot AI"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "Opspilot-Backend"
    }
