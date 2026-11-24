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