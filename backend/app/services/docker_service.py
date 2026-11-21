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

        # it converts into absolute path
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
        
        except DockerException as exc:

            logger.exception(
                "Docker Engine connection failed"
            )

            raise RuntimeError(
                f"Unable to connect to Docker Engine: {str(exc)}"
            )
    
    # --------------------------------
    # 2. Check Docker Engine
    # --------------------------------
    def health_check(self):

        try:

            if self.client is None:
                self.connect()
            
            info = self.client.info()

            return {
                "status": "healthy",
                "docker_version": self.client.version().get(
                    "Version"
                ),
                "operating_system": info.get("OperatingSystem"),
                "architecture": info.get("Architecture")
            }
        
        except Exception:

            logger.exception(
                "Docker health check failed"
            )

            return {
                "status": "unhealthy"
            }

    # --------------------------------
    # 3. Validate Docker Build Context
    # --------------------------------
    def validate_context(self, context_path):

        requested_path = Path(context_path).resolve()

        try:

            requested_path.relative_to(
                self.workspace_root
            )
        
        except ValueError:

            raise ValueError(
                "Build context must be inside the Docker workspace"
            )
        
        if not requested_path.is_dir():

            raise ValueError(
                "Docker build context directory does not exist"
            )
        
        dockerfile = requested_path / "Dockerfile"

        if not dockerfile.is_file():

            raise FileNotFoundError(
                "Dockerfile not found in repository"
            )
        
        # Check build context size
        total_size = 0

        for file in requested_path.rglob("*"):

            if file.is_symlink():
                raise ValueError(
                    "Symlinks are not allowed in build context"
                )
            
            if file.is_file():

                total_size += file.stat().st_size
        
        max_size = (
            settings.DOCKER_MAX_BUILD_CONTEXT_MB
            * 1024
            * 1024
        )

        if total_size > max_size:

            raise ValueError(
                "Docker build context exceeds maximum allowed size"
            )

        return requested_path
    
    # --------------------------------
    # 4. Validate Image Name and Tag
    # --------------------------------
    def validate_image_reference(self, image_name, image_tag):

        name_pattern = r"^[a-z0-9]+(?:[._/-][a-z0-9]+)*$"

        tag_pattern = r"^[a-zA-Z0-9_][a-zA-Z0-9_.-]{0,127}$"

        if not re.fullmatch(name_pattern, image_name):

            raise ValueError(
                "Invalid Docker image name"
            )
        
        if not re.fullmatch(tag_pattern, image_tag):

            raise ValueError(
                "Invalid Docker image tag"
            )
        
        return f"{image_name}:{image_tag}"
    
    # --------------------------------
    # 5. Build Docker Image
    # --------------------------------
    def build_image(
        self,
        context_path,
        image_name,
        image_tag
    ):

        if self.client is None:
            self.connect()

        context = self.validate_context(
            context_path
        )

        image_reference = self.validate_image_reference(
            image_name,
            image_tag
        )

        try:

            logger.info(
                "Starting Docker build: %s",
                image_reference
            )

            image, build_logs = self.client.images.build(

                path = str(context),
                dockerfile = "Dockerfile",
                tag = image_reference,
                rm = True,
                pull = True,
                labels = {
                    "managed-by": "opspilot-ai"
                }
            )
        
            # Collect only build status messages.
            # Do not return raw build output to the API user.
            build_status = []

            for entry in build_logs:

                status = entry.get("status")

                if status:
                    build_status.append(status)
            
            image_details = self.client.api.inspect_image(
                image.id
            )

            result = {
                "success": True,

                "message": "Docker image built successfully",

                "image_id": image.id,

                "image_name": image_name,

                "image_tag": image_tag,

                "image_reference": image_reference,

                "image_size": image_details.get(
                    "Size",
                    0
                ),

                "build_status": build_status[-10:]

            }

            logger.info(
                "Docker image built successfully: %s",
                image_reference
            )

            return result
        
        except BuildError:

            logger.exception(
                "Docker image build failed"
            )

            raise RuntimeError(
                "Docker image build failed. Check worker logs."
            )
        
        except DockerException:

            logger.exception(
                "Docker operation failed"
            )

            raise RuntimeError(
                "Docker Engine operation failed"
            )

    # --------------------------------
    # 6. Inspect Docker Image
    # --------------------------------
    def inspect_image(self, image_reference):

        if self.client is None:
            self.connect()

        try:

            image = self.client.images.get(
                image_reference
            )

            details = self.client.api.inspect_image(
                image.id
            )

            return {
                "image_id": image.id,

                "tags": image.tags,

                "size": details.get("Size"),

                "created": details.get("Created"),

                "architecture": details.get("Architecture"),

                "os": details.get("Os")
            }

        except ImageNotFound:

            raise ValueError(
                "Docker image not found"
            )

    # --------------------------------
    # 7. Close Docker Connection
    # --------------------------------
    def close(self):

        if self.client:

            self.client.close()
            self.client = None

docker_service = DockerService()