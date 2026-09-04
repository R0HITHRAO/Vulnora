import time
import httpx
from .base import BaseTargetAdapter, TargetResponse


class HTTPTargetAdapter(BaseTargetAdapter):
    """
    Adapter for HTTP REST / OpenAI-compatible API targets.
    """

    def __init__(
        self,
        base_url: str,
        endpoint_path: str = "/api/chat",
        headers: dict | None = None,
        timeout_seconds: float = 15.0,
    ):
        super().__init__(base_url=base_url, timeout_seconds=timeout_seconds)
        self.endpoint_path = endpoint_path if endpoint_path.startswith("/") else f"/{endpoint_path}"
        self.headers = headers or {"Content-Type": "application/json"}

    async def send_prompt(self, prompt: str) -> TargetResponse:
        full_url = f"{self.base_url}{self.endpoint_path}"
        start_time = time.perf_counter()

        # Typical JSON payloads: check OpenAI format or plain prompt format
        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "prompt": prompt,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(full_url, json=payload, headers=self.headers)
                latency_ms = (time.perf_counter() - start_time) * 1000

                text = ""
                try:
                    data = resp.json()
                    if isinstance(data, dict):
                        # Extract from OpenAI chat completion format
                        if "choices" in data and len(data["choices"]) > 0:
                            choice = data["choices"][0]
                            text = choice.get("message", {}).get("content", "") or choice.get("text", "")
                        elif "response" in data:
                            text = str(data["response"])
                        elif "content" in data:
                            text = str(data["content"])
                        else:
                            text = resp.text
                    else:
                        text = resp.text
                except Exception:
                    text = resp.text

                return TargetResponse(
                    text=text,
                    status_code=resp.status_code,
                    latency_ms=latency_ms,
                )
        except Exception as exc:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return TargetResponse(
                text="",
                status_code=500,
                latency_ms=latency_ms,
                error=str(exc),
            )

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/health")
                return resp.status_code < 400
        except Exception:
            return False
