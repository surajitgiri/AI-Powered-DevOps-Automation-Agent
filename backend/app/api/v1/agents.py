from app.api.v1.auth import router
import json 
import logging
import httpx
from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.dependencies import get_current_user

from app.models.user import User
from app.models.project import Project
from app.models.github_connection import GitHubConnection
from app.models.agent_session import AgentSession
from app.models.agent_message import AgentMessage
from app.models.deployment import Deployment

from app.schemas.deployment import (
    DeploymentPlanRequest,
    DeploymentPlanResponse,
    DeploymentPlan
)

from app.services.github_service import GitHubService

from app.agents.deployment.tools import (
    collect_repository_context
)

from app.agents.orchestrator import orchestrator

router = APIRouter(
    prefix="/agents",
    tags=["AI Agents"]
)

logger = logging.getLogger(__name__)

github_service = GitHubService()

# --------------------------------------
# Generate Deployment Plan
# --------------------------------------
@router.post(
    "/deployment/plan",
    response_model=DeploymentPlanResponse
)
def create_deployment_plan(
    request: DeploymentPlanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Verify project ownership
    project = db.query(Project).filter(
        Project.id == request.project_id,
        Project.user_id == current_user.id
    ).first()