from pydantic import BaseModel, Field
from typing import Optional, Literal

class DockerBuildRequest(BaseModel):

    project_id: str

    deployment_id: Optional[str] = None

    context_path: str

    image_name: str

    image_tag: str = "latest"
    

class DockerBuildResponse(BaseModel):

    success: bool

    message: str

    image_id: Optional[str] = None

    image_name: Optional[str] = None

    image_tag: Optional[str] = None

    image_size: Optional[int] = None

# For Gemini
class DockerfileGenerateRequest(BaseModel):

    project_id: str
    branch: Optional[str] = None
    application_type: Optional[
        Literal["nextjs", "nodejs", "fastapi"]
    ] = None

class DockerfileGenerateResponse(BaseModel):

    success: bool
    project_id: str
    repository: str
    detected_framework: str
    dockerfile: str
    dockerignore: str
    message: str

# Github Clone
class GitHubCloneRequest(BaseModel):

    project_id: str
    branch: Optional[str] = None

class GitHubCloneResponse(BaseModel):

    success: bool

    workspace_id: str

    repository: str

    branch: str

    framework: str

    files: dict

    message: str

# Dockerfile Persistence + Human Approval + Asynchronous Docker Build.
class PrepareBuildRequest(BaseModel):
    project_id: str
    workspace_id: str
    branch: Optional[str] = None
    application_type: Optional[str] = None

class PrepareBuildResponse(BaseModel):
    success: bool
    workspace_id: str
    repository: str
    branch: str
    framework: str
    dockerfile: str
    dockerignore: str
    message: str

# -----------------------------------------
# Docker Build Approval
# -----------------------------------------
class DockerBuildApprovalRequest(BaseModel):
    project_id: str
    workspace_id: str
    image_name: str
    image_tag: str = "v1"

class DockerBuildApprovalResponse(BaseModel):

    success: bool
    deployment_id: str
    approval_id: str
    status: str
    message: str

# -----------------------------------------
# Docker Build Approval Decision
# -----------------------------------------
class DockerBuildApprovalDecision(BaseModel):

    action: Literal["approve", "reject"]
    remarks: Optional[str] = None

# -----------------------------------------
# Docker Build Status
# -----------------------------------------
class DockerBuildStatusResponse(BaseModel):

    deployment_id: str

    status: str

    docker_image: Optional[str] = None

    image_id: Optional[str] = None

    image_size: Optional[int] = None

    error_message: Optional[str] = None