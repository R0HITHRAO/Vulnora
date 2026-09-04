from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel


class TargetResponse(BaseModel):
    text: str
    status_code: int = 200
    latency_ms: float = 0.0
    raw_payload: Optional[dict] = None
    error: Optional[str] = None


class BaseTargetAdapter(ABC):
    def __init__(self, base_url: str, timeout_seconds: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    @abstractmethod
    async def send_prompt(self, prompt: str) -> TargetResponse:
        """Send a test payload/prompt to the target system and return the response."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify target connectivity and responsiveness."""
        pass
