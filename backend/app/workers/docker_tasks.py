import logging
from pathlib import Path

from app.workers.celery_app import celery_app
from app.core.database import SessionLocal

from app.models.deployment import Deployment
from app.services.docker_service import docker_service
from app.core.config import settings

logger = logging.getLogger(__name__)

@celery_app.task(
    bind=True,
    name="docker.build_image",
    max_retries=0
)
def build_docker_image(
    self,
    deployment_id: str,
    user_id: str,
    project_id: str,
    workspace_id: str,
    image_name: str,
    image_tag: str
):

    db = SessionLocal()

    try:

       deployment = db.query(Deployment).filter(
            Deployment.id == deployment_id,
            Deployment.user_id == user_id,
            Deployment.project_id == project_id
        ).first()
       
       if not deployment:
        raise ValueError("Deployment not found")
       
       # Mark build as running.
       deployment.status = "building"
       db.commit()

       workspace_root = Path(
        settings.GITHUB_CLONE_WORKSPACE
       ).resolve()

       context_path = (
            workspace_root
            / str(user_id)
            / str(project_id)
            / str(workspace_id)
       ).resolve()

       context_path.relative_to(workspace_root)

       # Build Docker Image
       result = docker_service.build_image(
        context_path = str(context_path),
        image_name = image_name,
        image_tag = image_tag
       )

       # save image details
       deployment.docker_image = result["image_reference"]
       deployment.image_digest = result["image_id"]
       deployment.status = "build_success"

       db.commit()

       logger.info(
          "Docker build completed: %s",
            result["image_reference"]
       )

       return {
           "success": True,
            "deployment_id": deployment_id,
            "image_reference": result["image_reference"],
            "image_id": result["image_id"],
            "image_size": result["image_size"]
        }
    
    except Exception as exc:

        db.rollback()

        logger.exception(
            "Docker build failed for deployment %s",
            deployment_id
        )

        deployment = db.query(Deployment).filter(
            Deployment.id == deployment_id
        ).first()

        if deployment:
            deployment.status = "build_failed"
            deployment.error_message = str(exc)
            db.commit()
        
        raise

    finally:

        docker_service.close()
        db.close()