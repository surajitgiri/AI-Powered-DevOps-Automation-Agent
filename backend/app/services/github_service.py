import boto3
import httpx
import json
from urllib.parse import urlencode

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
            "client_id": settings.GITHUB_CLIENT_ID.strip(),
            "redirect_uri": settings.GITHUB_CALLBACK_URL.strip(),
            "scope": "repo read:user",
            "state": state
        }

        query = urlencode(params)

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
            err = data.get("error_description") or data.get("error") or "GitHub did not return an access token"
            raise ValueError(f"GitHub token exchange failed: {err}")
        
        return access_token

    # --------------------------------
    # 3. Common GitHub API request
    # --------------------------------

    def github_request(
        self,
        access_token: str,
        endpoint: str,
        params: dict | None = None
    ):
      
      response = httpx.get(
        f"{GITHUB_API}{endpoint}",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        },
        params=params,
        timeout=20
      )

      response.raise_for_status()

      return response.json()

    
    # --------------------------------
    # 4. Get GitHub user
    # --------------------------------
    def get_github_user(self, access_token: str):

        return self.github_request(
            access_token,
            "/user"
        )

    # --------------------------------
    # 5. List repositories
    # --------------------------------
    def get_repositories(self, access_token: str):

        repositories = []

        page = 1

        while True:

            data = self.github_request(
                access_token,
                "/user/repos",
                {
                    "sort": "updated",
                    "per_page": 100,
                    "page": page,
                    "affiliation": "owner,collaborator,organization_member"
                }
            )

            if not data:
                break

            repositories.extend(data)

            if len(data) < 100:
                break

            page += 1

        return  repositories

    # --------------------------------
    # 6. Get branches
    # --------------------------------

    def get_branches(
        self,
        access_token: str,
        owner: str,
        repository: str
    ):

        return self.github_request(
            access_token,
            f"/repos/{owner}/{repository}/branches",
            {
                "per_page": 100
            }
        )

    # --------------------------------
    # 7. Get latest commit
    # --------------------------------

    def get_latest_commit(
        self,
        access_token: str,
        owner: str,
        repository: str,
        branch: str
    ):

        data = self.github_request(
            access_token,
            f"/repos/{owner}/{repository}/commits/{branch}"
        )

        return data

    # --------------------------------
    # 8. Save token in AWS Secrets Manager
    # --------------------------------

    def save_token(
        self,
        user_id: str,
        project_id: str,
        access_token: str
    ):

        secret_name = (
            f"opspilot/github/{user_id}/{project_id}"
        )

        secret_value = json.dumps({
            "access_token": access_token
        })

        try:

            result = self.secrets_client.create_secret(
                Name=secret_name,
                SecretString=secret_value,
                Description="OpsPilot AI GitHub OAuth token"
            )

            return result["ARN"]

        except self.secrets_client.exceptions.ResourceExistsException:

            result = self.secrets_client.put_secret_value(
                SecretId=secret_name,
                SecretString=secret_value
            )

            return result["ARN"]

    # --------------------------------
    # 9. Retrieve token
    # --------------------------------

    def get_token(self, secret_ref: str):

        result = self.secrets_client.get_secret_value(
            SecretId=secret_ref
        )

        secret = json.loads(
            result["SecretString"]
        )

        return secret["access_token"]