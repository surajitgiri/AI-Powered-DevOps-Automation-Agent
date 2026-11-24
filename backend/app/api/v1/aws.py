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
from app.models.deployment import Deployment

from app.schemas.aws import (
    AWSConnectionResponse,
    ECRPushRequest,
    ECRPushResponse
)

from app.services.aws_service import aws_service
from app.services.ecr_service import ecr_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/aws",
    tags=["AWS Integration"]
)

# --------------------------------
# 1. AWS Connection Health Check
# --------------------------------
@router.get("/health")
def aws_health_check(
    current_user: User = Depends(get_current_user)
):

    result = aws_service.health_check()

    if result["status"] != "healthy":

        raise HTTPException(
            status_code=503,
            detail="AWS connection unavailable"
        )

    return result

# --------------------------------
# 2. Push Docker Image to ECR
# --------------------------------
@router.post(
    "/ecr/push",
    response_model = ECRPushResponse
)
def push_docker_image(
    request: ECRPushRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):  
    # Verify deployment ownership
    deployment = db.query(Deployment).filter(
        Deployment.id == request.deployment_id,
        Deployment.user_id == current_user.id
    ).first()

    if not deployment:

        raise HTTPException(
            status_code = 404,
            detail = "Deployment not found"
        )
    
    # Ensure Docker build succeeded
    if deployment.status != "build_success":

        raise HTTPException(
            status_code = 400,
            detail = "Docker image has not been built successfully"
        )
    
    if not deployment.docker_image:

        raise HTTPException(
            status_code = 400,
            detail = "Docker image reference not found"
        )
    
    try:

        # Push image to ECR
        result = ecr_service.push_image(
            local_image = deployment.docker_image,
            repository_name = request.repository_name,
            image_tag = request.image_tag
        )

        # Update deployment record
        deployment.docker_image = result["image_uri"]
        deployment.image_digest = result["image_digest"]
        deployment.status = "image_pushed"

        db.commit()

        return {
            "success": True,

            "deployment_id": str(deployment.id),

            "repository_uri": result["repository_uri"],

            "image_uri": result["image_uri"],

            "image_digest": result["image_digest"],

            "message": "Docker image successfully pushed to AWS ECR"
        }
    
    except HTTPException:
        raise

    except Exception:

        db.rollback()

        logger.exception(
            "ECR push API failed"
        )

        raise HTTPException(
            status_code = 502,
            detail = "Unable to push Docker image to AWS ECR"
        )