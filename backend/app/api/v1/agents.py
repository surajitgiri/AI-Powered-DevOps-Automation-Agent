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

    if not project:

        raise HTTPException(
            status_code=404,
            detail="Project not found"
        )

    # ----------------------------------
    # 2. Get GitHub connection
    # ----------------------------------
    github_connection = db.query(
        GitHubConnection
    ).filter(
        GitHubConnection.user_id == current_user.id,
        GitHubConnection.project_id == project.id,
        GitHubConnection.is_active.is_(True)
    ).first()

    if not github_connection:

        raise HTTPException(

            status_code=404,

            detail="GitHub account is not connected"

        )
    
    if not github_connection.repository_name:

        raise HTTPException(

            status_code=400,

            detail="No GitHub repository is connected to this project"

        )
    
    # ----------------------------------
    # 3. Retrieve GitHub access token
    # ----------------------------------
    try:

        access_token = github_service.get_token(
            github_connection.token_secret_ref
        )

    except Exception:

        logger.exception("Failed to retrieve GitHub token")

        raise HTTPException(
            status_code=502,
            detail="Unable to access the connected GitHub account"
        )
    
    # ----------------------------------
    # 4. Identify repository and branch
    # ----------------------------------
    repository = github_connection.repository_name

    branch = (
        request.branch
        or project.default_branch
        or "main"
    )

    repository_url = github_connection.repository_url

    if not repository_url:

        raise HTTPException(
            status_code=400,
            detail="Repository URL is missing"
        )
    
    # ----------------------------------
    # 5. Retrieve latest commit
    # ----------------------------------