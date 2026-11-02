from pathlib import Path

from dotenv import load_dotenv

# Load backend/.env regardless of the working directory
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

import os

from langchain_ollama import ChatOllama

from langchain_core.messages import HumanMessage, SystemMessage

llm = ChatOllama(
    model=os.getenv("OLLAMA_MODEL", "llama3.2"),
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    temperature=0
)

SYSTEM_PROMPT = """
You are OpsPilot AI, an intelligent DevOps assistant.

Your responsibilities:

1. Understand DevOps requests.
2. Identify the required operations.
3. Generate structured execution plans.
4. Identify security risks.
5. Request human approval before execution.

You must never execute arbitrary commands.

For deployment requests, generate a step-by-step plan.

Return clear and structured responses.
"""

async def process_request(user_prompt: str):

    message = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_prompt)
    ]

    response = await llm.ainvoke(message)

    return {
        "request": user_prompt,
        "response": response.content
    }