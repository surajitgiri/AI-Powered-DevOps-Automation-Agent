from pydantic import BaseModel, Field
from typing import Optional

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