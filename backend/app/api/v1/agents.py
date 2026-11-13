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
    try:
        owner, repo_name = repository.split("/", 1)

        commit = github_service.get_latest_commit(
            access_token,
            owner,
            repo_name,
            branch
        )

        commit_sha = commit["sha"]

    except Exception:

        logger.exception("Failed to retrieve GitHub commit")
        raise HTTPException(
            status_code=502,
            detail="Unable to retrieve the selected branch or commit"
        )

    # ----------------------------------
    # 6. Inspect repository
    # ----------------------------------
    try:

        repository_context = collect_repository_context(
            access_token,
            repository,
            branch
        )

    except Exception:

        logger.exception("Repository inspection failed")
        raise HTTPException(
            status_code=502,
            detail="Unable to inspect GitHub repository"
        )
    
    # ----------------------------------
    # 7. Build agent state
    # ----------------------------------
    deployment_target = (
        getattr(project, "deployment_platform", None)

        or "AWS EC2"
    )

    initial_state = {
        "user_prompt": request.prompt,
        "project_id": str(project.id),
        "project_name": project.name,
        "repository": repository,
        "repository_url": repository_url,
        "branch": branch,
        "commit_sha": commit_sha,
        "repository_context": repository_context,
        "environment": request.environment,
        "deployment_target": deployment_target
    }

    # ----------------------------------
    # 8. Run AI Deployment Agent
    # ----------------------------------
    try:

        plan_data = orchestrator.run(
            agent_type="deployment",
            state=initial_state
        )

        plan = DeploymentPlan.model_validate(
            plan_data
        )
    except Exception:

        logger.exception("AI deployment planning failed")

        raise HTTPException(
            status_code=502,
            detail="Unable to generate deployment plan"
        )
    
    # ----------------------------------
    # 9. Save Agent Session
    # ----------------------------------
    try:

        session = AgentSession(
            user_id = current_user.id,
            project_id = project.id,
            title = f"Deployment planning - {project.name}",
            agent_type = "deployment",
            status = "completed"

        )

        db.add(session)
        db.flush()
    
        # ----------------------------------
        # 10. Save User Message
        # ----------------------------------
        user_message = AgentMessage(
            session_id = session.id,
            role = "user",
            content = request.prompt
        )

        db.add(user_message)

        # ----------------------------------
        # 11. Save AI Response
        # ----------------------------------

        assistant_message = AgentMessage(
            session_id = session.id,
            role = "assistant",
            content = json.dumps(
                plan.model_dump(mode="json")
            ),

            message_metadata={

                "agent_type": "deployment",

                "model": "gemini",

                "branch": branch,

                "commit_sha": commit_sha

            }
        )

        db.add(assistant_message)

        # ----------------------------------
        # 12. Save Deployment Plan
        # ----------------------------------

        deployment = Deployment(
            project_id = project.id,

            user_id = current_user.id,

            session_id = session.id,

            environment = request.environment,

            repository_url = repository_url,

            branch = branch,

            commit_sha = commit_sha,

            status = "plan_generated",

            deployment_plan = plan.model_dump(mode="json")
        )

        db.add(deployment)
        db.commit()
        db.refresh(deployment)
        db.refresh(session)

        return DeploymentPlanResponse(
            deployment_id=deployment.id,

            session_id=session.id,

            project_id=project.id,

            project_name=project.name,

            repository=repository,

            branch=branch,

            commit_sha=commit_sha,

            status=deployment.status,

            plan=plan
        )
    except Exception:

        db.rollback()

        logger.exception("Failed to save deployment plan")
        raise HTTPException(
            status_code=500,
            detail="Failed to save deployment plan"
        )


# --------------------------------------
# Retrieve Deployment Plan
# --------------------------------------
@router.get("/deployment/{deployment_id}")
def get_deployment_plan(
    deployment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    deployment = db.query(Deployment).filter(
        Deployment.id == deployment_id,
        Deployment.user_id == current_user.id
    ).first()

    if not deployment:

        raise HTTPException(
            status_code=404,
            detail="Deployment not found"
        )
    
    return {
        "deployment_id": str(deployment.id),

        "project_id": str(deployment.project_id),

        "environment": deployment.environment,

        "repository_url": deployment.repository_url,

        "branch": deployment.branch,

        "commit_sha": deployment.commit_sha,

        "status": deployment.status,

        "deployment_plan": deployment.deployment_plan,

        "created_at": deployment.created_at

    }