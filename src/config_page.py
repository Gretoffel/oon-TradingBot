import streamlit as st
import json
import os
import sys

# Ensure src/ is on the path so ai_providers can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_providers import load_ai_config, save_ai_config, PROVIDERS, CONFIG_DIR

st.set_page_config(
    page_title="Trading Bot - AI Konfiguration",
    layout="centered",
    page_icon="settings",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    div[data-testid="stForm"] { border: 1px solid #444; border-radius: 10px; padding: 20px; }
    </style>
""",
    unsafe_allow_html=True,
)

st.title("AI Konfiguration")
st.caption("Waehle deinen AI-Provider und konfiguriere die Einstellungen.")

# Load current config
cfg = load_ai_config()

# Provider selection
provider_keys = list(PROVIDERS.keys())
provider_labels = list(PROVIDERS.values())
current_idx = provider_keys.index(cfg.get("provider", "google_studio")) if cfg.get("provider") in provider_keys else 0

selected_label = st.selectbox(
    "AI Provider",
    provider_labels,
    index=current_idx,
)
selected_provider = provider_keys[provider_labels.index(selected_label)]

st.markdown("---")

# Provider-specific settings
if selected_provider == "google_studio":
    st.info("Google AI Studio verwendet Browser-Automation. Kein API Key noetig. Du musst einmalig in Google eingeloggt sein.")

elif selected_provider == "openai":
    st.subheader("OpenAI Einstellungen")
    openai_cfg = cfg.get("openai", {})
    openai_key = st.text_input(
        "API Key",
        value=openai_cfg.get("api_key", ""),
        type="password",
        help="Dein OpenAI API Key (sk-...)",
    )
    openai_model = st.selectbox(
        "Modell",
        ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
        index=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"].index(
            openai_cfg.get("model", "gpt-4o")
        )
        if openai_cfg.get("model", "gpt-4o")
        in ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]
        else 0,
    )

elif selected_provider == "claude":
    st.subheader("Claude (Anthropic) Einstellungen")
    claude_cfg = cfg.get("claude", {})
    claude_key = st.text_input(
        "API Key",
        value=claude_cfg.get("api_key", ""),
        type="password",
        help="Dein Anthropic API Key (sk-ant-...)",
    )
    claude_models = [
        "claude-sonnet-4-5-20250929",
        "claude-haiku-4-5-20251001",
        "claude-opus-4-6",
    ]
    default_model = claude_cfg.get("model", "claude-sonnet-4-5-20250929")
    claude_model = st.selectbox(
        "Modell",
        claude_models,
        index=claude_models.index(default_model) if default_model in claude_models else 0,
    )

elif selected_provider == "google_api":
    st.subheader("Google Gemini API Einstellungen")
    google_cfg = cfg.get("google_api", {})
    google_key = st.text_input(
        "API Key",
        value=google_cfg.get("api_key", ""),
        type="password",
        help="Dein Google AI API Key",
    )
    google_models = ["gemini-2.0-flash", "gemini-2.0-pro", "gemini-1.5-flash", "gemini-1.5-pro"]
    default_gmodel = google_cfg.get("model", "gemini-2.0-flash")
    google_model = st.selectbox(
        "Modell",
        google_models,
        index=google_models.index(default_gmodel) if default_gmodel in google_models else 0,
    )

elif selected_provider == "ollama":
    st.subheader("Ollama Einstellungen")
    ollama_cfg = cfg.get("ollama", {})
    ollama_url = st.text_input(
        "Base URL",
        value=ollama_cfg.get("base_url", "http://localhost:11434"),
        help="Ollama Server URL (lokal oder remote HTTPS)",
    )
    ollama_model = st.text_input(
        "Modell",
        value=ollama_cfg.get("model", "llama3"),
        help="z.B. llama3, mistral, codellama, etc.",
    )

st.markdown("---")

# Save & Start
col1, col2 = st.columns(2)

with col1:
    if st.button("Speichern & Bot starten", type="primary"):
        # Build config
        new_cfg = dict(cfg)  # keep existing keys
        new_cfg["provider"] = selected_provider

        if selected_provider == "openai":
            new_cfg["openai"] = {"api_key": openai_key, "model": openai_model}
        elif selected_provider == "claude":
            new_cfg["claude"] = {"api_key": claude_key, "model": claude_model}
        elif selected_provider == "google_api":
            new_cfg["google_api"] = {"api_key": google_key, "model": google_model}
        elif selected_provider == "ollama":
            new_cfg["ollama"] = {"base_url": ollama_url, "model": ollama_model}

        save_ai_config(new_cfg)

        # Write start signal
        signal_file = os.path.join(CONFIG_DIR, ".start_bot")
        with open(signal_file, "w") as f:
            f.write("start")

        st.success(f"Gespeichert! Provider: {PROVIDERS[selected_provider]}")
        st.info("Bot startet gleich... Dieses Fenster kann geschlossen werden.")

with col2:
    if st.button("Nur speichern"):
        new_cfg = dict(cfg)
        new_cfg["provider"] = selected_provider

        if selected_provider == "openai":
            new_cfg["openai"] = {"api_key": openai_key, "model": openai_model}
        elif selected_provider == "claude":
            new_cfg["claude"] = {"api_key": claude_key, "model": claude_model}
        elif selected_provider == "google_api":
            new_cfg["google_api"] = {"api_key": google_key, "model": google_model}
        elif selected_provider == "ollama":
            new_cfg["ollama"] = {"base_url": ollama_url, "model": ollama_model}

        save_ai_config(new_cfg)
        st.success("Konfiguration gespeichert!")

# Show current config (read-only)
with st.expander("Aktuelle Konfiguration (JSON)"):
    st.json(load_ai_config())
