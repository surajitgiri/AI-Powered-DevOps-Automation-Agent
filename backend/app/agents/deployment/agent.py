import json
from typing import Any
from google import genai
from google.genai import types
from langgraph.graph import StateGraph, START, END
from app.core.config import settings
from app.agents.state import DeploymentAgentState
from app.agents.prompts import (
    DEPLOYMENT_SYSTEM_PROMPT,
    DEPLOYMENT_USER_PROMPT
)
from app.schemas.deployment import DeploymentPlan

# --------------------------------------
# Initialize Google GenAI Client
# --------------------------------------

def get_client() -> genai.Client:
    return genai.Client(api_key=settings.GEMINI_API_KEY)

# --------------------------------------
# Node 1: Generate Deployment Plan
# --------------------------------------

def generate_deployment_paln(
    state: DeploymentAgentState
):
    client = get_client()

    user_prompt = DEPLOYMENT_USER_PROMPT.format(
        user_prompt=state["user_prompt"],
        project_name=state["project_name"],
        repository=state["repository"],
        repository_url=state["repository_url"],
        branch=state["branch"],
        commit_sha=state["commit_sha"],
        environment=state["environment"],
        deployment_target=state["deployment_target"],
        repository_context=json.dumps(
            state["repository_context"],
            indent=2
        )
    )

    full_prompt = f"{DEPLOYMENT_SYSTEM_PROMPT}\n\n{user_prompt}"

    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=full_prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=DeploymentPlan,
            temperature=0.0
        ),
    )

    plan = DeploymentPlan.model_validate_json(response.text)

    # Backend-controlled fields must not be changed by the LLM.
    plan = plan.model_copy(
        update={
            "branch": state["branch"],
            "commit_sha": state["commit_sha"],
            "deployment_target": state["deployment_target"],
            "requires_approval": True,
            "execution_allowed": False
        }
    )

    return {
        "plan": plan.model_dump(mode="json")
    }

# --------------------------------------
# Node 2: Validate Deployment Plan
# --------------------------------------
def validate_deployment_plan(
    state: DeploymentAgentState
):
    plan = DeploymentPlan.model_validate(
        state["plan"]
    )

    if len(plan.steps) < 3:
        raise ValueError(
            "Deployment plan must contain at least 3 steps"
        )
    
    if plan.execution_allowed is not False:
        raise ValueError(
            "Deployment execution is not permitted"
        )
    
    if plan.requires_approval is not True:
        raise ValueError(
            "Human approval is mandatory"
        )

    return {
        "plan": plan.model_dump(mode="json")
    }

# --------------------------------------
# Build LangGraph workflow
# --------------------------------------
def build_deployment_graph():
    graph = StateGraph(
        DeploymentAgentState
    )

    graph.add_node(
        "generate_plan",
        generate_deployment_paln
    )

    graph.add_node(
        "validate_plan",
        validate_deployment_plan
    )

    graph.add_edge(
        START,
        "generate_plan"
    )

    graph.add_edge(
        "generate_plan",
        "validate_plan"
    )

    graph.add_edge(
        "validate_plan",
        END
    )

    return graph.compile()

# --------------------------------------
# Execute Planning Agent
# --------------------------------------
def run_deployment_planner(
    initial_state: dict[str, Any]
):
    deployment_graph = build_deployment_graph()

    result = deployment_graph.invoke(
        initial_state
    )

    return result["plan"]
