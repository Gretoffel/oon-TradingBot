from ai_providers.base_provider import AIProvider


class ClaudeProvider(AIProvider):
    """Anthropic Claude API provider."""

    name = "claude"

    def __init__(self, api_key, model="claude-sonnet-4-5-20250929"):
        self.api_key = api_key
        self.model = model
        self.client = None

    def _get_client(self):
        if self.client is None:
            from anthropic import AsyncAnthropic
            self.client = AsyncAnthropic(api_key=self.api_key)
        return self.client

    async def send_prompt(self, prompt: str):
        try:
            client = self._get_client()
            response = await client.messages.create(
                model=self.model,
                max_tokens=4096,
                system="You are a financial data analyst. Always respond with valid JSON only. No markdown, no explanations outside the JSON.",
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text
            if text:
                print("\n" + "-" * 50)
                print(f"RAW AI RESPONSE ({self.model}):")
                print("-" * 50)
                print(text)
                print("-" * 50 + "\n")
            return text
        except Exception as e:
            print(f"AI Error (Claude): {e}")
            return None
