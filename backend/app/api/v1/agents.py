from fastapi import APIRouter
from pydantic import BaseModel
from app.agents.orchestrator import process_request

router = APIRouter()

class AgentRequest(BaseModel):
    prompt: str

@router.post("/execute")
async def execute_agent(request: AgentRequest):
    result = await process_request(request.prompt)

    return result