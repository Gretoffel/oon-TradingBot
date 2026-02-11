from ai_providers.base_provider import AIProvider


class OpenAIProvider(AIProvider):
    """OpenAI API provider (GPT-4o, etc.)."""

    name = "openai"

    def __init__(self, api_key, model="gpt-4o"):
        self.api_key = api_key
        self.model = model
        self.client = None

    def _get_client(self):
        if self.client is None:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(api_key=self.api_key)
        return self.client

    async def send_prompt(self, prompt: str):
        try:
            client = self._get_client()
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a financial data analyst. Always respond with valid JSON only. No markdown, no explanations outside the JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )
            text = response.choices[0].message.content
            if text:
                print("\n" + "-" * 50)
                print(f"RAW AI RESPONSE ({self.model}):")
                print("-" * 50)
                print(text)
                print("-" * 50 + "\n")
            return text
        except Exception as e:
            print(f"AI Error (OpenAI): {e}")
            return None
