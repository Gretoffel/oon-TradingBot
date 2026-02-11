class AIProvider:
    """Base class for all AI providers."""

    name = "base"

    async def send_prompt(self, prompt: str):
        """Send a prompt and return the raw text response, or None on failure."""
        raise NotImplementedError

    async def cleanup(self):
        """Optional cleanup (e.g. close browser pages)."""
        pass
