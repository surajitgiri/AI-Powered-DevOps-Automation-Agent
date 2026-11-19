import logging
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

from app.schemas.docker import (
    GitHubCloneRequest,
    GitHubCloneResponse,
    DockerfileGenerateRequest,
    DockerfileGenerateResponse
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