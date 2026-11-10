from pydantic import HttpUrl
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query
)

from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from itsdangerous import (
    URLSafeTimedSerializer,
    BadSignature,
    SignatureExpired
)

from app.core.config import settings
from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.github_connection import GitHubConnection
from app.schemas.github import ConnectRepositoryRequest
from app.services.github_service import GitHubService

router = APIRouter(
    prefix="/github",
    tags=["GitHub Integration"]
)

github_service = GitHubService()

state_serializer = URLSafeTimedSerializer(
    settings.GITHUB_STATE_SECRET,
    salt="github-oauth-state"
)


# --------------------------------
# 1. Start GitHub OAuth
# --------------------------------

@router.get("/connect")
def connect_github(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == current_user.id
    ).first()

    if not project:

        raise HTTPException(
            status_code=404,
            detail="Project not found"
        )

    state = state_serializer.dumps({
        "user_id": str(current_user.id),
        "project_id": str(project.id)
    })

    authorization_url = (
        github_service.get_authorization_url(state)
    )

    return {
        "authorization_url": authorization_url
    }

# --------------------------------
# 2. GitHub OAuth callback
# --------------------------------

@router.get("/callback")
def github_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db)
):

    try:

        state_data = state_serializer.loads(
            state,
            max_age=600
            )

    except SignatureExpired:

        raise HTTPException(
            status_code = 400,
            detail="GitHub OAuth state expired. Try again."
        )
    
    except BadSignature:

        raise HTTPException(
            status_code=400,
            detail="Invalid GitHub OAuth state"
        )

    user_id = state_data["user_id"]
    project_id = state_data["project_id"]

    user = db.query(User).filter(
        User.id == user_id,
        User.is_active == True
    ).first()

    if not user:

        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == user.id
    ).first()

    if not project:

        raise HTTPException(
            status_code=404,
            detail="Project not found"
        )

    try:

        # Exchange authorization code for access token
        access_token = github_service.exchange_code(code)

        # Get GitHub profile
        github_user = github_service.get_github_user(
            access_token
        )

        # Store token securely
        secret_ref = github_service.save_token(
            str(user.id),
            str(project.id),
            access_token
        )

        # Check existing connection
        connection = db.query(GitHubConnection).filter(
            GitHubConnection.user_id == user.id,
            GitHubConnection.project_id == project.id
        ).first()

        if connection:

            connection.github_username = github_user["login"]
            connection.token_secret_ref = secret_ref
            connection.is_active = True

        else:

            connection = GitHubConnection(
                user_id=user.id,
                project_id=project.id,
                github_username=github_user["login"],
                token_secret_ref=secret_ref,
                repository_url=None,
                repository_name=None,
                is_active=True
            )

            db.add(connection)

        db.commit()

        return RedirectResponse(
            url=(
                f"{settings.FRONTEND_URL}/dashboard/settings"
                "?github=connected"
            )
        )
    
    except Exception as e:

        db.rollback()
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"GitHub connection failed: {str(e)}"
        )

# --------------------------------
# 3. List GitHub repositories
# --------------------------------


@router.get("/repositories")
def get_repositories(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    connection = db.query(GitHubConnection).filter(
        GitHubConnection.user_id == current_user.id,
        GitHubConnection.project_id == project_id,
        GitHubConnection.is_active == True
    ).first()

    if not connection:

        raise HTTPException(
            status_code=404,
            detail="GitHub account not connected"
        )

    try:

        access_token = github_service.get_token(
            connection.token_secret_ref
        )

        repositories = github_service.get_repositories(
            access_token
        )

        return [
            {
                "id": repo["id"],
                "name": repo["name"],
                "full_name": repo["full_name"],
                "html_url": repo["html_url"],
                "private": repo["private"],
                "default_branch": repo["default_branch"]
            }
            for repo in repositories
        ]
    
    except Exception:

        raise HTTPException(
            status_code=502,
            detail="Unable to retrieve GitHub repositories"
        )

# --------------------------------
# 4. Connect repository to project
# --------------------------------

@router.post("/connect-repository")
def connect_repository(
    request: ConnectRepositoryRequest,
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
            detail="Connect GitHub account first"
        )

    try:

        access_token = github_service.get_token(
            connection.token_secret_ref
        )

         # Verify repository access before connecting
        owner, repository = request.repository_full_name.split("/", 1)

        github_repo = github_service.github_request(
            access_token,
            f"/repos/{owner}/{repository}"
        )

        if github_repo["html_url"] != str(request.repository_url):

            raise HTTPException(
                status_code=400,
                detail="Repository URL does not match GitHub repository"
            )

         # Save repository information
          # Save repository information
        connection.repository_name = github_repo["full_name"]

        connection.repository_url = github_repo["html_url"]

        db.commit()

        return {
            "message": "Repository connected successfully",
            "project_id": str(project.id),
            "repository": connection.repository_name,
            "default_branch": github_repo["default_branch"]
        }

    except HTTPException:
        raise

    except Exception:
        db.rollback() 

        raise HTTPException(
            status_code=502,
            detail="Unable to connect repository"
        )

# --------------------------------
# 5. List repository branches
# --------------------------------

@router.get("/branches")
def get_repository_branches(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    connection = db.query(GitHubConnection).filter(
        GitHubConnection.user_id == current_user.id,
        GitHubConnection.project_id == project_id,
        GitHubConnection.is_active == True
    ).first()

    if not connection or not connection.repository_name:

        raise HTTPException(
            status_code=404,
            detail="Repository not connected"
        )

    try:

        access_token = github_service.get_token(
            connection.token_secret_ref
        )

        owner, repository = connection.repository_name.split("/", 1)

        branches = github_service.get_branches(
            access_token,
            owner,
            repository
        )

        return [
            {
                "name": branch["name"],
                "commit_sha": branch["commit"]["sha"]
            }
            for branch in branches
        ]
    
    except Exception:

        raise HTTPException(
            status_code=502,
            detail="Unable to retrieve branches"
        )

# --------------------------------
# 6. Get latest commit
# --------------------------------
@router.get("/latest-commit")
def get_latest_commit(
    project_id: str,
    branch: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

     connection = db.query(GitHubConnection).filter(
        GitHubConnection.user_id == current_user.id,
        GitHubConnection.project_id == project_id,
        GitHubConnection.is_active == True
    ).first()

     if not connection or not connection.repository_name:

        raise HTTPException(
            status_code=404,
            detail="Repository not connected"
        )

     try:

        access_token =  github_service.get_token(
            connection.token_secret_ref
        )

        owner, repository = connection.repository_name.split("/", 1)

        commit = github_service.get_latest_commit(
            access_token,
            owner,
            repository,
            branch
        )

        return {
            "repository": connection.repository_name,
            "branch": branch,
            "commit_sha": commit["sha"],
            "commit_message": commit["commit"]["message"],
            "author": commit["commit"]["author"]["name"]
        }

     except Exception:

        raise HTTPException(
            status_code=502,
            detail="Unable to retrieve latest commit"
        )