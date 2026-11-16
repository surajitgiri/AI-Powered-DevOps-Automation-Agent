import logging

from app.workers.celery_app import celery_app
from app.services.docker_service import DockerService

logger = logging.getLogger(__name__)

@celery_app.task(
    name="docker.build_image",
    bind=True
)
def build_docker_image(
    self,
    context_path: str,
    image_name: str,
    image_tag: str
):

    docker_service = DockerService()

    try:

        logger.info(
            "Docker build task started: %s:%s",
            image_name,
            image_tag
        )

        result = docker_service.build_image(
            context_path=context_path,
            image_name=image_name,
            image_tag=image_tag
        )

        logger.info(
            "Docker build task completed"
        )

        return result
    
    except Exception:

        logger.exception(
            "Docker build task failed"
        )

        raise

    finally:

        docker_service.close()