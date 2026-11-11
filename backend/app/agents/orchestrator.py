from app.agents.deployment.agent import (
    run_deployment_planner
)

class AgentOrchestrator:

    def __init__(self):

        self.agents = {
            "deployment": run_deployment_planner
        }
    
    def run(
        self,
        agent_type: str,
        state: dict
    ):

        agent = self.agents.get(agent_type)

        if not agent:

            raise ValueError(
                f"Agent type '{agent_type}' is not supported"
            )
        
        return agent(state)

# Global orchestrator
orchestrator = AgentOrchestrator()