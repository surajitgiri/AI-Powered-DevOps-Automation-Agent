import logging
import boto3

from botocore.exceptions import (
    ClientError,
    BotoCoreError
)

from app.core.config import settings

logger = logging.getLogger(__name__)

class AWSService:
    def __init__(self):

        self.region = settings.AWS_REGION
        self.profile = settings.AWS_PROFILE
        self.session = None
    
    # --------------------------------
    # 1. Create AWS Session
    # --------------------------------
    def connect(self):

        try:

            session_kwargs = {
                "region_name": self.region
            }

            if self.profile:
                session_kwargs["profile_name"] = self.profile
            
            self.session = boto3.Session(
                **session_kwargs
            )

            identity = self.session.client(
                "sts"
            ).get_caller_identity()

            logger.info(
                "AWS connected successfully: %s",
                identity["Arn"]
            )

            return {
                "connected": True,
                "account_id": identity["Account"],
                "arn": identity["Arn"],
                "region": self.region
            }
        
        except (ClientError, BotoCoreError):

            logger.exception(
                "AWS connection failed"
            )

            raise RuntimeError(
                "Unable to connect to AWS"
            )
    

    # --------------------------------
    # 2. Get AWS Client
    # --------------------------------
    def get_client(self, service_name):

        if self.session is None:
            self.connect()
        
        return self.session.client(
            service_name,
            region_name = self.region
        )
    
    # --------------------------------
    # 3. Get AWS Resource
    # --------------------------------
    def get_resource(self, service_name):

        if self.session is None:
            self.connect()
        
        return self.session.resource(
            service_name,
            region_name = self.region
        )
    
    # --------------------------------
    # 4. Check AWS Connection
    # --------------------------------
    def health_check(self):


        try:

            client = self.get_client("sts")

            identity = client.get_caller_identity()

            return {
                "status": "healthy",
                "account_id": identity["Account"],
                "region": self.region
            }
        
        except Exception:

            logger.exception(
                "AWS health check failed"
            )

            return {
                "status": "unhealthy"
            }

aws_service = AWSService()