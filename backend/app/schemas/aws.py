from pydantic import BaseModel, Field
from typing import Optional

# --------------------------------
# AWS Connection
# --------------------------------
class AWSConnectionResponse(BaseModel):
     connected: bool

     account_id: str

     arn: str

     region: str

# --------------------------------
# ECR Push Request
# --------------------------------
class ECRPushRequest(BaseModel):

    deployment_id: str

    repository_name: str = Field(
        min_length=2,
        max_length=256
    )

    image_tag: str = Field(
        min_length=1,
        max_length=128
    )

# --------------------------------
# ECR Push Response
# --------------------------------
class ECRPushResponse(BaseModel):

    success: bool

    deployment_id: str

    repository_uri: str

    image_uri: str

    image_digest: Optional[str] = None

    message: str