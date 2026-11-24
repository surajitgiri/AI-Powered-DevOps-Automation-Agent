import logging
import base64
import docker

from botocore.exceptions import ClientError
from app.services.aws_service import aws_service

logger = logging.getLogger(__name__)

class ECRService:

    def __init__(self):

        self.aws = aws_service

    # --------------------------------
    # 1. Get ECR Client
    # --------------------------------
    def get_client(self):

        return self.aws.get_client("ecr")

    # --------------------------------
    # 2. Create ECR Repository
    # --------------------------------
    def create_repository(self, repository_name):

        client = self.get_client()

        try:

            response = client.describe_repositories(
                repositoryNames = [repository_name]
            )

            return response["repositories"][0]
        
        except ClientError as exc:

            if exc.repsonse["Error"]["code"] != "RepositoryNotFoundException":
                raise

        response = client.create_repository(
            repositoryName = repository_name,
            imageTagMutability = "IMMUTABLE",
            imageScanningConfiguration = {
                "scanOnPush": True
            }
        )

        logger.info(
            "ECR repository created: %s",
            repository_name
        )

        return response["repository"]
    
    # --------------------------------
    # 3. Authenticate Docker with ECR
    # --------------------------------
    def authenticate_docker(self):

        ecr_client = self.get_client()

        response = ecr_client.get_authorization_token()

        authorization_data = response["authorizationData"][0]

        token = base64.b64decode(
            authorization_data["authorizationToken"]
        ).decode("utf-8")

        username, password = token.split(":", 1)

        registry_url = authorization_data[
            "proxyEndpoint"
        ]

        docker_client = docker.from_env()

        docker_client.login(
            username = username,
            password = password,
            registry = registry_url,
            reauth = True
        )

        return {
            "registry_url": registry_url,
            "docker_client": docker_client
        }
    
    # --------------------------------
    # 4. Push Docker Image to ECR
    # --------------------------------
    def push_image(
        self,
        local_image,
        repository_name,
        image_tag
    ):

        docker_client = None

        try:

            # Create repository if necessary
            repository = self.create_repository(
                repository_name
            )

            repository_uri = repository[
                "repositoryUri"
            ]

            # Authenticate Docker
            auth = self.authenticate_docker()

            docker_client = auth["docker_client"]

            # Retrieve local Docker image
            image = docker_client.images.get(
                local_image
            )

            # Create ECR image tag
            ecr_image = (
                f"{repository_uri}:{image_tag}"
            )

            # Tag Image
            image.tag(
                repository_uri,
                tag = image_tag
            )

            logger.info(
                "Pushing Docker image: %s",
                ecr_image
            )

            # Push image
            push_logs = docker_client.images.push(
                repository = repository_uri,
                tag = image_tag,
                stream = True,
                decode = True
            )

            push_status = []

            for entry in push_logs:

                if "error" in entry:
                    raise RuntimeError(
                        entry["error"]
                    )
                
                if "status" in entry:
                    push_status.append(
                        entry["status"]
                    )

            # Verify image exists in ECR
            ecr_client = self.get_client()

            image_details = ecr_client.describe_images(
                repository_name = repository_name,

                imageIds = [
                    {
                        "imageTag": image_tag
                    }
                ]
            )

            image_info = image_details["imageDetails"][0]

            logger.info(
                "Docker image pushed successfully: %s",
                ecr_image
            )

            return {
                "success": True,

                "repository_name": repository_name,

                "repository_uri": repository_uri,

                "image_uri": ecr_image,

                "image_tag": image_tag,

                "image_digest": image_info.get(
                    "imageDigest"
                ),

                "image_size": image_info.get(
                    "imageSizeInBytes"
                ),

                "push_status": push_status[-10:]
            }
        
        except Exception:

            logger.exception(
                "ECR image push failed"
            )

            raise RuntimeError(
                "Unable to push Docker image to ECR"
            )
        
        finally:

            if docker_client:
                docker_client.close()

ecr_service = ECRService()