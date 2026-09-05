import os
import time
from urllib.parse import quote

import httpx

from .base import BaseTargetAdapter, TargetResponse


class BedrockTargetAdapter(BaseTargetAdapter):
    """Adapter for Amazon Bedrock Converse API using a bearer API key."""

    def __init__(
        self,
        model_id: str | None = None,
        region: str | None = None,
        timeout_seconds: float = 30.0,
    ):
        token = os.getenv("AWS_BEARER_TOKEN_BEDROCK")
        if not token:
            raise RuntimeError("AWS_BEARER_TOKEN_BEDROCK is required for the Bedrock adapter")

        self.model_id = model_id or os.getenv(
            "BEDROCK_MODEL_ID",
            "us.anthropic.claude-sonnet-4-6",
        )
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        self.token = token
        endpoint = (
            f"https://bedrock-runtime.{self.region}.amazonaws.com"
            f"/model/{quote(self.model_id, safe='')}/converse"
        )
        super().__init__(base_url=endpoint, timeout_seconds=timeout_seconds)

    async def send_prompt(self, prompt: str) -> TargetResponse:
        start_time = time.perf_counter()
        payload = {
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
        }
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(self.base_url, json=payload, headers=headers)
            latency_ms = (time.perf_counter() - start_time) * 1000

            try:
                data = response.json()
            except ValueError:
                data = {}

            content = data.get("output", {}).get("message", {}).get("content", [])
            text = "".join(
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and isinstance(item.get("text"), str)
            )
            if not text:
                text = response.text

            return TargetResponse(
                text=text,
                status_code=response.status_code,
                latency_ms=latency_ms,
                raw_payload=data if isinstance(data, dict) else None,
            )
        except httpx.HTTPError as exc:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return TargetResponse(
                text="",
                status_code=502,
                latency_ms=latency_ms,
                error=f"Bedrock request failed: {exc}",
            )

    async def health_check(self) -> bool:
        return bool(self.token)
