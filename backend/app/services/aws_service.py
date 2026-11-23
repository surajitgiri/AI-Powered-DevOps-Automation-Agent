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