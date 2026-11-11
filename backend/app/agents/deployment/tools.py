from botocore import endpoint
import base64
import httpx
from urllib.parse import quote
from app.services.github_service import GitHubService

github_service = GitHubService()

SAFE_REPOSITORY_FILES = [
    "README.md",
    "package.json",
    "requirements.txt",
    "pyproject.toml",
    "Dockerfile",
    "docker-compose.yml",
    "go.mod",
    "Cargo.toml"
]

# --------------------------------------
# Get repository metadata
# --------------------------------------
def get_repository_metadata(
    access_token: str,
    repository: str
):

    owner, repo_name = repository.split("/", 1)

    endpoint = (
        f"/repos/{quote(owner, safe='')}/"
        f"{quote(repo_name, safe='')}"
    )

    return github_service.github_request(
        access_token,
        endpoint
    )

# --------------------------------------
# Get repository file
# --------------------------------------

def get_repository_file(
    access_token: str,
    repository: str,
    file_path: str,
    branch: str
):

    if file_path not in SAFE_REPOSITORY_FILES:

        raise ValueError("File is not in the allowed inspection list")

    owner, repo_name = repository.split("/", 1)

    encoded_path = quote(file_path, safe="/")

    endpoint = (
        f"/repos/{quote(owner, safe='')}/"
        f"{quote(repo_name, safe='')}/contents/{encoded_path}"
    )

    try:

        data = github_service.github_request(
            access_token,
            endpoint,
            {
                "ref": branch
            }
        )

        if data.get("encoding") != "base64":
            return None
        
        content = base64.b64decode(
            data["content"]
        ).decode(
            "utf-8",
            errors="replace"
        )

        # Limit content sent to the LLM.
        return content[:12000]
    
    except httpx.HTTPStatusError as error:

        if error.response.status_code == 404:
            return None
        
        raise

# --------------------------------------
# Collect repository context
# --------------------------------------
def collect_repository_context(
    access_token: str,
    repository: str,
    branch: str
):

    metadata = get_repository_metadata(
        access_token,
        repository
    )

    files = {}

    for filename in SAFE_REPOSITORY_FILES:

        content = get_repository_file(
            access_token,
            repository,
            filename,
            branch
        )

        if content:

            files[filename] = content
    
    return {
        "repository": metadata["full_name"],

        "description": metadata.get("description"),

        "language": metadata.get("language"),

        "default_branch": metadata.get("default_branch"),

        "visibility": (
            "private" if metadata.get("private") else "public"
        ),

        "files": files
    }