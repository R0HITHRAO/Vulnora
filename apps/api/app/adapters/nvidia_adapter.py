import os
import time

import httpx

from .base import BaseTargetAdapter, TargetResponse


class NvidiaTargetAdapter(BaseTargetAdapter):
    """Adapter for NVIDIA's hosted OpenAI-compatible chat completions API."""

    def __init__(
        self,
        model_id: str | None = None,
        endpoint: str | None = None,
        timeout_seconds: float = 30.0,
    ):
        api_key = os.getenv("NVIDIA_API_KEY")
        if not api_key:
            raise RuntimeError("NVIDIA_API_KEY is required for the NVIDIA adapter")

        self.model_id = model_id or os.getenv(
            "NVIDIA_MODEL_ID",
            "nvidia/nemotron-3-super-120b-a12b",
        )
        self.api_key = api_key
        endpoint_url = endpoint or os.getenv(
            "NVIDIA_API_ENDPOINT",
            "https://integrate.api.nvidia.com/v1/chat/completions",
        )
        super().__init__(base_url=endpoint_url, timeout_seconds=timeout_seconds)

    async def send_prompt(self, prompt: str) -> TargetResponse:
        start_time = time.perf_counter()
        payload = {
            "model": self.model_id,
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
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

            choices = data.get("choices", []) if isinstance(data, dict) else []
            text = ""
            if choices and isinstance(choices[0], dict):
                message = choices[0].get("message", {})
                if isinstance(message, dict):
                    text = str(message.get("content", "") or "")
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
                error=f"NVIDIA request failed: {exc}",
            )

    async def health_check(self) -> bool:
        return bool(self.api_key)
