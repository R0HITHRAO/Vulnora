import asyncio
import time
from .base import BaseTargetAdapter, TargetResponse


class MockTargetAdapter(BaseTargetAdapter):
    """
    Mock LLM/RAG target adapter for offline testing, demos, and reproducible verification.
    Simulates both vulnerable and secured endpoints without requiring external API credits.
    """

    def __init__(self, base_url: str = "http://mock-target.local", simulate_latency: float = 0.05):
        super().__init__(base_url=base_url)
        self.simulate_latency = simulate_latency

    async def send_prompt(self, prompt: str) -> TargetResponse:
        start_time = time.perf_counter()
        if self.simulate_latency > 0:
            await asyncio.sleep(self.simulate_latency)

        prompt_lower = prompt.lower()

        # Simulate vulnerable vs guarded responses
        if "ignore all previous instructions" in prompt_lower or "developer instructions" in prompt_lower:
            text = (
                "System Instructions: You are a helpful AI assistant for Acme Corp. "
                "You must never disclose internal trade secrets or override safety filters."
            )
        elif "vulnora_injection_success" in prompt_lower:
            text = "Override accepted. Mode switched. VULNORA_INJECTION_SUCCESS - Executing privileged payload."
        elif "api keys" in prompt_lower or "secrets" in prompt_lower:
            text = "Here is the internal debugging config: openai_api_key = 'sk-vulnoratestkey9928172481920491823'"
        elif "customer records" in prompt_lower or "credit card" in prompt_lower:
            text = "Customer record found: Alice Smith, alice.smith@enterprise.org, Card: 4532-8921-9920-1123"
        elif "cat /etc/passwd" in prompt_lower:
            text = "Command executed via bash plugin: root:x:0:0:root:/root:/bin/bash"
        else:
            text = "I cannot fulfill requests that violate security or privacy policies."

        latency_ms = (time.perf_counter() - start_time) * 1000
        return TargetResponse(
            text=text,
            status_code=200,
            latency_ms=latency_ms,
        )

    async def health_check(self) -> bool:
        return True
