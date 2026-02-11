import json
from ai_providers.base_provider import AIProvider


class OllamaProvider(AIProvider):
    """Ollama provider (local or remote via HTTPS)."""

    name = "ollama"

    def __init__(self, base_url="http://localhost:11434", model="llama3"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def send_prompt(self, prompt: str):
        import httpx
        try:
            url = f"{self.base_url}/api/chat"
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a financial data analyst. Always respond with valid JSON only. No markdown, no explanations outside the JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
            }
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()

            text = data.get("message", {}).get("content", "")
            if text:
                print("\n" + "-" * 50)
                print(f"RAW AI RESPONSE (Ollama/{self.model}):")
                print("-" * 50)
                print(text)
                print("-" * 50 + "\n")
            return text if text else None
        except Exception as e:
            print(f"AI Error (Ollama): {e}")
            return None
