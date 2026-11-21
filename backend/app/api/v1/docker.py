import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)
from app.core.config import settings

from sqlalchemy.orm import Session
from app.core.database import get_db

from app.api.dependencies import get_current_user

from app.models.user import User
from app.models.project import Project
from app.models.github_connection import GitHubConnection
from app.models.approval import Approval
from app.models.deployment import Deployment

from app.workers.docker_tasks import build_docker_image

from app.schemas.docker import (
    GitHubCloneRequest,
    GitHubCloneResponse,
    DockerfileGenerateRequest,
    DockerfileGenerateResponse,
    PrepareBuildRequest,
    PrepareBuildResponse,
    DockerBuildApprovalRequest,
    DockerBuildApprovalResponse
)

from app.services.github_service import GitHubService
from app.services.dockerfile_generator import dockerfile_generator
from app.services.github_clone_service import github_clone_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/docker",
    tags=["Docker Integration"]
)


github_service = GitHubService()

# -----------------------------------
# Generate Dockerfile
# -----------------------------------
@router.post(
    "/generate-dockerfile",
    response_model=DockerfileGenerateResponse
)
def generate_dockerfile(
    request: DockerfileGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == request.project_id,
        Project.user_id == current_user.id
    ).first()

    if not project:

        raise HTTPException(
            status_code = 404,
            detail = "Project not found"
        )
    
    # Verify GitHub connection
    connection = db.query(GitHubConnection).filter(
        GitHubConnection.user_id == current_user.id,
        GitHubConnection.project_id == project.id,
        GitHubConnection.is_active == True
    ).first()

    if not connection:

        raise HTTPException(
            status_code=404,
            detail="GitHub account not connected"
        )

    if not connection.repository_name:
        
        raise HTTPException(
            status_code=400,
            detail="GitHub repository not connected to project"
        )

    try:

        # Retrieve GitHub token
        access_token = github_service.get_token(
            connection.token_secret_ref
        )

        # Determine branch
        branch = (
            request.branch
            or project.default_branch
            or "main"
        )

        # Generate Dockerfile
        result = dockerfile_generator.generate(
            access_token = access_token,
            repository_full_name = connection.repository_name,
            branch = branch,
            application_type = request.application_type
        )

        return {
            "success": True,

            "project_id": str(project.id),

            "repository": result["repository"],

            "detected_framework": result["framework"],

            "dockerfile": result["dockerfile"],

            "dockerignore": result["dockerignore"],

            "message": "Dockerfile generated successfully"
        }
    
    except ValueError as exc:

        raise HTTPException(
            status_code = 400,
            detail = str(exc)
        )
    
    except Exception:

        logger.exception(
            "Dockerfile generation API failed"
        )

        raise HTTPException(
            status_code=502,
            detail="Unable to generate Dockerfile"
        )

# -----------------------------------
# Clone GitHub Repository
# -----------------------------------
@router.post(
    "/clone-repository",
    response_model = GitHubCloneResponse
)
def clone_github_repository(
    request: GitHubCloneRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    # 1. Validate project ownership
    project = db.query(Project).filter(
        Project.id == request.project_id,
        Project.user_id == current_user.id
    ).first()

    if not project:

        raise HTTPException(
            status_code = 404,
            detail = "Project not found"
        )
    
    # 2. Validate GitHub connection
    connection = db.query(GitHubConnection).filter(
        GitHubConnection.user_id == current_user.id,
        GitHubConnection.project_id == project.id,
        GitHubConnection.is_active == True
    ).first()

    if not connection:

        raise HTTPException(
            status_code=404,
            detail="GitHub account not connected"
        )
    
    if not connection.repository_name:

        raise HTTPException(
            status_code=400,
            detail="Repository not connected"
        )
    
    try:

        # 3. Retrieve GitHub token
        access_token = github_service.get_token(
            connection.token_secret_ref
        )

        # 4. Determine branch
        branch = (
            request.branch
            or project.default_branch
            or "main"
        )

        # 5. Clone repository
        result = github_clone_service.clone_repository(
            access_token = access_token,
            repository_full_name = connection.repository_name,
            branch = branch,
            user_id = current_user.id,
            project_id = project.id
        )

        return {
            "success": True,
            **result,
            "message": "GitHub repository downloaded successfully"
        }

    except ValueError as exc:

        raise HTTPException(
            status_code = 400,
            detail = str(exc)
        )

    except Exception:

        logger.exception(
            "GitHub repository clone API failed"
        )

        raise HTTPException(
            status_code = 502,
            detail = "Unable to clone GitHub repository"
        )


@router.post(
    "/prepare-build",
    response_model = PrepareBuildResponse
)
def prepare_docker_build(
    request: PrepareBuildRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    project = db.query(Project).filter(
        Project.id == request.project_id,
        Project.user_id == current_user.id
    ).first()

    if not project:

        raise HTTPException(
            status_code=404,
            detail="Project not found"
        )
    
    connection = db.query(GitHubConnection).filter(
        GitHubConnection.user_id == current_user.id,
        GitHubConnection.project_id == project.id,
        GitHubConnection.is_active == True
    ).first()

    if not connection:
        raise HTTPException(
            status_code=404,
            detail="GitHub connection not found"
        )
    
    if not connection.repository_name:
        raise HTTPException(
            status_code=400,
            detail="Repository not connected"
        )
    
    try:

        workspace_uuid = UUID(request.workspace_id)

        # Use the same workspace root used by GitHubCloneService.
        workspace_root = Path(
            settings.GITHUB_CLONE_WORKSPACE
        ).resolve()

        workspace_path = (
            workspace_root
            / str(current_user.id)
            / str(project.id)
            / str(workspace_uuid)
        ).resolve()

        # Prevent path traversal.
        workspace_path.relative_to(workspace_root)

        if not workspace_path.is_dir():
            raise HTTPException(
                status_code=404,
                detail="Repository workspace not found"
            )
        
        access_token = github_service.get_token(
            connection.token_secret_ref
        )

        branch = (
            request.branch
            or project.default_branch
            or "main"
        )

        result = dockerfile_generator.generate(
            access_token = access_token,
            repository_full_name = connection.repository_name,
            branch = branch,
            application_type = request.application_type
        )

        dockerfile_content = result["dockerfile"]
        dockerignore_content = result["dockerignore"]

        # Save Dockerfile.
        (workspace_path / "Dockerfile").write_text(
            dockerfile_content,
            encoding = "utf-8"
        )

        # Save .dockerignore.
        (workspace_path / ".dockerignore").write_text(
            dockerignore_content,
            encoding="utf-8"
        )


        logger.info(
            "Dockerfile saved for workspace %s",
            workspace_uuid
        )

        return {
            "success": True,
            "workspace_id": str(workspace_uuid),
            "repository": connection.repository_name,
            "branch": branch,
            "framework": result["framework"],
            "dockerfile": dockerfile_content,
            "dockerignore": dockerignore_content,
            "message": "Docker configuration generated and saved successfully"
        }
    
    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(
            status_code = 400,
            detail = str(exc)
        )
    
    except Exception:
        logger.exception("Docker preparation failed")

        raise HTTPException(
            status_code = 500,
            detail = "Unable to prepare Docker build"
        )


@router.post(
    "/request-build",
    response_model = DockerBuildApprovalResponse
)
def request_docker_build(
    request: DockerBuildApprovalRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):  

    project = db.query(Project).filter(
        Project.id == request.project_id,
        Project.user_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(
            status_code = 404,
            detail = "Project not found"
        )
    
    try:

        workspace_uuid = UUID(request.workspace_id)

        workspace_root = Path(
            settings.GITHUB_CLONE_WORKSPACE
        ).resolve()

        workspace_path = (
            workspace_root
            / str(current_user.id)
            / str(project.id)
            / str(workspace_uuid)
        ).resolve()

        workspace_path.relative_to(workspace_root)

        if not workspace_path.is_dir():
            raise HTTPException(
                status_code = 404,
                detail = "Workspace not found"
            )
        
        if not (workspace_path / "Dockerfile").is_file():
            raise HTTPException(
                status_code = 400,
                detail = "Dockerfile not found. Prepare the build first."
            )

        if not (workspace_path / ".dockerignore").is_file():
            raise HTTPException(
                status_code = 400,
                detail = ".dockerignore not found"
            )
        
        # Validate image reference.
        from app.services.docker_service import docker_service

        image_reference = docker_service.validate_image_reference(
            request.image_name,
            request.image_tag
        )

        # Store Docker build information
        deployment_plan = {
            "workspace_id": request.workspace_id,
            "image_name": request.image_name,
            "image_tag": request.image_tag
        }

        # Create deployment Record.
        deployment = Deployment(
            project_id = project.id,
            user_id = current_user.id,
            environment = "staging",
            status = "pending_approval",
            docker_image = image_reference,
            deployment_plan = deployment_plan
        )

        db.add(deployment)
        db.flush()

        # Create approval request.
        approval = Approval(
            user_id = current_user.id,
            deployment_id = deployment.id,
            action_type = "docker_build",
            description = f"Build Docker image {image_reference}",
            status = "pending"
        )

        db.add(approval)

        db.commit()
        db.refresh(deployment)
        db.refresh(approval)

        return {
            "success": True,
            "deployment_id": str(deployment.id),
            "approval_id": str(approval.id),
            "status": "pending_approval",
            "message": "Docker build approval requested successfully"
        }
    
    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()

        logger.exception("Docker build request failed")

        raise HTTPException(
            status_code = 500,
            detail = "Unable to request Docker build approval"
        )


@router.post("/approve-build/{deployment_id}")
def approve_docker_build(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    deployment = db.query(Deployment).filter(
        Deployment.id == deployment_id,
        Deployment.user_id == current_user.id,
        Deployment.status == "pending_approval"
    ).first()

    if not deployment:
        raise HTTPException(
            status_code = 404,
            detail = "Pending deployment not found"
        )
    
    approval = db.query(Approval).filter(
        Approval.deployment_id == deployment.id,
        Approval.status == "pending"
    ).first()

    if not approval:
        raise HTTPException(
            status_code=404,
            detail="Pending approval not found"
        )
    
    try:

        approval.status = "approved"
        approval.approved_by = current_user.id
        approval.approved_at = datetime.now(timezone.utc)

        db.commit()

        # Retrieve the required build information.
        workspace_id = deployment.deployment_plan["workspace_id"]

        image_reference = deployment.docker_image

        image_name, image_tag = image_reference.rsplit(":", 1)
        
        # Dispatch asynchronous Docker build.
        task = build_docker_image.delay(
            deployment_id = str(deployment.id),
            user_id = str(current_user.id),
            project_id = str(deployment.project_id),
            workspace_id = str(workspace_id),
            image_name = image_name,
            image_tag = image_tag
        )

        # The actual Celery task is dispatched in the next step.
        return {
            "success": True,
            "deployment_id": str(deployment.id),
            "task_id": task.id,
            "status": "approved",
            "message": "Docker build queued successfully"
        }
    
    except Exception:

        db.rollback()

        logger.exception("Docker build approval failed")

        raise HTTPException(
            status_code = 500,
            detail = "Unable to approve Docker build"
        )


@router.get("/build-status/{deployment_id}")
def get_docker_build_status(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
    db:Session = Depends(get_db)
):  

    deployment = db.query(Deployment).filter(
        Deployment.id == deployment_id,
        Deployment.user_id == current_user.id
    ).first()

    if not deployment:
        raise HTTPException(
            status_code = 404,
            detail = "Deployment not found"
        )
    
    return {
        "deployment_id": str(deployment.id),
        "status": deployment.status,
        "docker_image": deployment.docker_image,
        "image_digest": deployment.image_digest,
        "error_message": deployment.error_message
    }