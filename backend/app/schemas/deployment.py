from typing import Literal, Optional

from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# -----------------------------------
# Deployment Plan Step
# -----------------------------------

class DeploymentPlanStep(BaseModel):

    step_number: int

    name: str

    description: str

    category: Literal[
        "source",
        "build",
        "containerization",
        "registry",
        "deployment",
        "verification",
        "configuration"
    ]


# -----------------------------------
# Environment Variables
# -----------------------------------

class EnvironmentVariable(BaseModel):

    name: str

    description: str

    required: bool = True


# -----------------------------------
# Complete Deployment Plan
# -----------------------------------

class DeploymentPlan(BaseModel):

    summary: str

    application_type: str

    detected_language: str

    detected_framework: Optional[str] = None

    package_manager: Optional[str] = None

    deployment_target: str

    branch: str

    commit_sha: str

    dockerization_needed: bool

    steps: list[DeploymentPlanStep] = Field(
        min_length=3,
        max_length=15
    )

    environment_variables: list[EnvironmentVariable] = Field(
        default_factory=list
    )

    prerequisites: list[str] = Field(
        default_factory=list
    )

    risks: list[str] = Field(
        default_factory=list
    )

    estimated_duration_minutes: int = Field(
        ge=1,
        le=1440
    )

    confidence: float = Field(
        ge=0,
        le=1
    )

    requires_approval: Literal[True] = True

    execution_allowed: Literal[False] = False


# -----------------------------------
# User Planning Request
# -----------------------------------

class DeploymentPlanRequest(BaseModel):

    project_id: UUID

    prompt: str = Field(
        min_length=10,
        max_length=2000
    )

    branch: Optional[str] = None

    environment: Literal[
        "development",
        "staging",
        "production"
    ] = "staging"


# -----------------------------------
# Deployment Plan Response
# -----------------------------------

class DeploymentPlanResponse(BaseModel):

    deployment_id: UUID

    session_id: UUID

    project_id: UUID

    project_name: str

    repository: str

    branch: str

    commit_sha: str

    status: str

    plan: DeploymentPlan


# -----------------------------------
# Existing Deployment Retrieval
# -----------------------------------

class DeploymentDetailsResponse(BaseModel):

    id: UUID

    project_id: UUID

    environment: str

    branch: Optional[str]

    commit_sha: Optional[str]

    status: str

    deployment_plan: Optional[dict]

    model_config = ConfigDict(from_attributes=True)