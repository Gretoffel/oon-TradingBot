from ai_providers.base_provider import AIProvider


class GoogleAPIProvider(AIProvider):
    """Google Gemini API provider."""

    name = "google_api"

    def __init__(self, api_key, model="gemini-2.0-flash"):
        self.api_key = api_key
        self.model_name = model
        self.model = None

    def _get_model(self):
        if self.model is None:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(
                self.model_name,
                system_instruction="You are a financial data analyst. Always respond with valid JSON only. No markdown, no explanations outside the JSON.",
            )
        return self.model

    async def send_prompt(self, prompt: str):
        import asyncio
        try:
            model = self._get_model()
            # google-generativeai is synchronous, run in executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: model.generate_content(prompt)
            )
            text = response.text
            if text:
                print("\n" + "-" * 50)
                print(f"RAW AI RESPONSE ({self.model_name}):")
                print("-" * 50)
                print(text)
                print("-" * 50 + "\n")
            return text
        except Exception as e:
            print(f"AI Error (Google API): {e}")
            return None
