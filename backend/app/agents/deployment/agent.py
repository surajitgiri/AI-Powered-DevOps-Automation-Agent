import json
from typing import Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from app.core.config import settings
from app.agents.state import DeploymentAgentState
from app.agents.prompts import (
    DEPLOYMENT_SYSTEM_PROMPT,
    DEPLOYMENT_USER_PROMPT
)
from app.schemas.deployment import DeploymentPlan