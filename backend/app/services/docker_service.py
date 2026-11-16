import os
import re
import logging

from pathlib import Path
import docker

from docker.errors import (
    DockerException,
    BuildError,
    ImageNotFound
)

from app.core.config import settings

logger = logging.getLogger(__name__)

class DockerService:

    def __init__(self):

        self.client = None
        self.enabled = settings.DOCKER_BUILD_ENABLED

        self.workspace_root = Path(
            settings.DOCKER_BUILD_CONTEXT_ROOT
        ).resolve()

    # --------------------------------
    # 1. Connect to Docker Engine
    # --------------------------------
    def connect(self):

        if not self.enabled:

            raise RuntimeError(
                "Docker build integration is disabled"
            )
        
        try:

            self.client = docker.from_env()
            self.client.ping()

            logger.info(
                "Docker Engine connected successfully"
            )

            return True
        
        except DockerException:

            logger.exception(
                "Docker Engine connection failed"
            )

            raise RuntimeError(
                "Unable to connect to Docker Engine"
            )
    