from pydantic import BaseModel, HttpUrl
from typing import Optional

class GitHubRepository(BaseModel):
    id: int

    name: str

    full_name: str

    html_url: HttpUrl

    private: bool

    default_branch: str

class ConnectRepositoryRequest(BaseModel):

    project_id: str

    repository_full_name: str

    repository_url: HttpUrl

    default_branch: str

class GitHubConnectionResponse(BaseModel):

    id: str

    github_username: str

    repository_name: Optional[str] = None

    repository_url: Optional[str] = None

    is_active: bool

class GitHubBranch(BaseModel):

    name: str

    commit_sha: str