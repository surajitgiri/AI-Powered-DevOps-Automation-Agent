from typing import TypedDict, Optional, Any

class DeploymentAgentState(TypedDict, total=False):
    # User request
    user_prompt: str

    # Project information
    project_id: str

    project_name: str

    # GitHub information
    repository: str

    repository_url: str

    branch: str

    commit_sha: str

    repository_context: dict[str, Any]

    # Deployment information
    environment: str

    deployment_target: str

    # AI generated output
    plan: Optional[dict]

    # Error handling
    error: Optional[str]