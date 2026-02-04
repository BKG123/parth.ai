"""Agent Manager - Wrapper for ReactiveAgent."""

from ai.reactive_agent import ReactiveAgent


class AgentManager:
    """Wrapper for managing reactive agent interactions."""

    def __init__(self, user_id: str, name: str = "Parth AI", model: str = "gpt-5-mini"):
        self.user_id = user_id
        self.reactive_agent = ReactiveAgent(user_id=user_id, name=name, model=model)

    async def stream_response(self, prompt: str, history: list[dict] = None):
        """Stream response from reactive agent."""
        async for event in self.reactive_agent.stream_response(prompt, history):
            yield event

    async def get_response(self, prompt: str, history: list[dict] = None) -> str:
        """Get complete response from reactive agent."""
        return await self.reactive_agent.get_response(prompt, history)

    @property
    def model_name(self) -> str:
        return self.reactive_agent.model_name

    @property
    def agent_name(self) -> str:
        return self.reactive_agent.agent_name
