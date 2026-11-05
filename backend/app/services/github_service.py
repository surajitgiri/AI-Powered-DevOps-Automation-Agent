from urllib import response
from dns.tsig import Key
import boto3
import httpx
import json

from botocore.exceptions import ClientError
from app.core.config import settings

GITHUB_API = "https://api.github.com"

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"

GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"

class GitHubService:

    def __init__(self):

        self.secrets_client = boto3.client(
            "secretsmanager",
            region_name=settings.AWS_REGION
        )

    # --------------------------------
    # 1. Generate OAuth URL
    # --------------------------------

    def get_authorization_url(self, state: str):

        params = {
            "client_id": settings.GITHUB_CLIENT_ID,
            "redirect_uri": settings.GITHUB_CALLBACK_URL,
            "scope": "repo read:user",
            "state": state
        }

        query = "&".join(
            f"{Key} = {httpx.QueryParams({Key: value})[key]}"
            for key, value in params.items()
        )

        return f"{GITHUB_AUTHORIZE_URL}?{query}"

     # --------------------------------
    # 2. Exchange code for token
    # --------------------------------

    def exchange_code(self, code: str):
        response = httpx.post(
            GITHUB_TOKEN_URL,
            headers={
                "Accept": "application/json"
            },
            json={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.GITHUB_CALLBACK_URL
            },
            timeout=20
        )

        response.raise_for_status()

        data = response.json()

        access_token = data.get("access_token")

        if not access_token:
            raise ValueError(
                "GitHub did not return an access token"
            )
        
        return access_token