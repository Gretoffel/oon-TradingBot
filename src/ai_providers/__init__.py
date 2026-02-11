import json
import os

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
CONFIG_FILE = os.path.join(CONFIG_DIR, "ai_config.json")

PROVIDERS = {
    "google_studio": "Google AI Studio (Browser)",
    "google_api": "Google Gemini API",
    "openai": "OpenAI API",
    "claude": "Claude (Anthropic) API",
    "ollama": "Ollama (Lokal/HTTPS)",
}


def load_ai_config():
    """Load the AI config from config/ai_config.json."""
    if not os.path.exists(CONFIG_FILE):
        return {"provider": "google_studio"}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"provider": "google_studio"}


def save_ai_config(data):
    """Save AI config to config/ai_config.json."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def create_provider(browser_context=None):
    """Create the AI provider based on the saved config.

    browser_context is only needed for google_studio provider.
    """
    cfg = load_ai_config()
    provider_name = cfg.get("provider", "google_studio")

    if provider_name == "google_studio":
        from ai_providers.google_studio_provider import GoogleStudioProvider
        if browser_context is None:
            raise ValueError("Google Studio provider requires a browser context.")
        return GoogleStudioProvider(browser_context)

    elif provider_name == "openai":
        from ai_providers.openai_provider import OpenAIProvider
        settings = cfg.get("openai", {})
        api_key = settings.get("api_key", "")
        model = settings.get("model", "gpt-4o")
        if not api_key:
            raise ValueError("OpenAI API Key ist nicht konfiguriert! Starte mit WEB_CONFIG=true.")
        return OpenAIProvider(api_key, model)

    elif provider_name == "claude":
        from ai_providers.claude_provider import ClaudeProvider
        settings = cfg.get("claude", {})
        api_key = settings.get("api_key", "")
        model = settings.get("model", "claude-sonnet-4-5-20250929")
        if not api_key:
            raise ValueError("Claude API Key ist nicht konfiguriert! Starte mit WEB_CONFIG=true.")
        return ClaudeProvider(api_key, model)

    elif provider_name == "google_api":
        from ai_providers.google_api_provider import GoogleAPIProvider
        settings = cfg.get("google_api", {})
        api_key = settings.get("api_key", "")
        model = settings.get("model", "gemini-2.0-flash")
        if not api_key:
            raise ValueError("Google API Key ist nicht konfiguriert! Starte mit WEB_CONFIG=true.")
        return GoogleAPIProvider(api_key, model)

    elif provider_name == "ollama":
        from ai_providers.ollama_provider import OllamaProvider
        settings = cfg.get("ollama", {})
        base_url = settings.get("base_url", "http://localhost:11434")
        model = settings.get("model", "llama3")
        return OllamaProvider(base_url, model)

    else:
        raise ValueError(f"Unbekannter AI Provider: {provider_name}")
