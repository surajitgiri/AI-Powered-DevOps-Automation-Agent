from fastapi import APIRouter
from app.api.v1 import auth, projects, github, agents
api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(projects.router)
api_router.include_router(github.router)
api_router.include_router(agents.router)