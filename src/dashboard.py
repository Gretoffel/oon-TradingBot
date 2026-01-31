# dashboard.py
import streamlit as st
import remote_manager
import utils
import time
import pandas as pd

st.set_page_config(page_title="Trading Bot Remote", layout="centered", page_icon="🤖")

# --- CSS Styling für besseren Look ---
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; }
    .big-font { font-size:20px !important; }
    </style>
""", unsafe_allow_html=True)

st.title("🤖 Trading Bot Controller")

# 1. Daten laden
state = remote_manager.get_state()
command = remote_manager.get_command()
logs = utils.get_todays_log_content()

# Berechne Zeit seit letztem Update
last_update = time.time() - state.get("timestamp", 0)
is_online = last_update < 120  # Wenn älter als 2 Min, gilt Bot als offline

# 2. STATUS HEADER
col1, col2 = st.columns(2)

with col1:
    st.metric("Verfügbares Cash", f"{state.get('balance', 0):.2f} €")

with col2:
    if is_online:
        if command == "stop":
            st.warning("⏸️ Bot PAUSIERT")
        elif state['phase'] == "Warten":
             st.info("💤 Schläft")
        else:
            st.success("🚀 Arbeitet")
    else:
        st.error("💀 Bot OFFLINE")

st.info(f"**Aktueller Status:** {state.get('phase', 'N/A')} - {state.get('details', 'N/A')}")

# 3. KONTROLLZENTRUM
st.markdown("### 🎮 Steuerung")
btn_col1, btn_col2 = st.columns(2)

with btn_col1:
    if st.button("▶️ STARTEN / WEITER", type="primary"):
        remote_manager.set_command("run")
        st.toast("Start-Befehl gesendet!")
        time.sleep(1)
        st.rerun()

with btn_col2:
    if st.button("⏹️ STOPPEN / PAUSIEREN"):
        remote_manager.set_command("stop")
        st.toast("Stop-Befehl gesendet! Bot stoppt nach aktuellem Schritt.", icon="🛑")
        time.sleep(1)
        st.rerun()

# 4. LOGS UND DETAILS
st.markdown("---")
st.markdown("### 📝 Heutige Aktivitäten")

# Logs schön in einer Box anzeigen
st.text_area("Log-Datei", logs, height=300)

# Auto-Refresh Button
if st.button("🔄 Aktualisieren"):
    st.rerun()

# Hinweis unten
st.caption(f"Letztes Signal vom Bot: vor {int(last_update)} Sekunden")