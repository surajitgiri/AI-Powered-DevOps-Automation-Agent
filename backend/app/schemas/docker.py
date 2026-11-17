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