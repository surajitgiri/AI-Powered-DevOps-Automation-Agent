from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from uuid import UUID
from app.core.database import get_db
from app.models.project import Project
from app.models.user import User
from app.api.dependencies import get_current_user

router = APIRouter()

class ProjectCreate(BaseModel):

    user_id: UUID

    name: str

    description: str | None = None

    repository_url: str | None = None

    repository_name: str | None = None

    default_branch: str = "main"


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_project(
    request: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify user exists
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id '{request.user_id}' not found"
        )

    project = Project(
        user_id=current_user.user_id,
        name=request.name,
        description=request.description,
        repository_url=request.repository_url,
        repository_name=request.repository_name,
        default_branch=request.default_branch
    )

    db.add(project)

    db.commit()

    db.refresh(project)

    return {
        "message": "Project created successfully",
        "project_id": str(project.id),
        "name": project.name
    }

@router.get("/")
def get_projects(db: Session = Depends(get_db),  current_user: User = Depends(get_current_user)):

    projects = db.query(Project).filter(
        Project.user_id == current_user.id
    ).all()

    return projects
