import streamlit as st
import remote_manager
import utils
import time
import pandas as pd

st.set_page_config(
    page_title="Trading Bot Remote", 
    layout="wide", 
    page_icon="🤖",
    initial_sidebar_state="collapsed"
)

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    .status-box { padding: 15px; border-radius: 10px; border: 1px solid #333; background-color: #1E1E1E; }
    .console-box { background-color: #0e0e0e; color: #00ff00; font-family: monospace; padding: 10px; border-radius: 5px; height: 400px; overflow-y: scroll; white-space: pre-wrap; border: 1px solid #444; font-size: 0.85em; }
    div[data-testid="stMetricValue"] { font-size: 28px; }
    </style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.title("🤖 OON Trading Bot Controller")

# --- AUTO REFRESH LOGIC ---
if 'last_run' not in st.session_state:
    st.session_state['last_run'] = time.time()

# Refresh rate in seconds
REFRESH_RATE = 2 

# 1. READ DATA
state = remote_manager.get_state()
command = remote_manager.get_command()
live_logs = remote_manager.get_live_logs(lines=100) # Read last 100 lines of console
daily_logs = utils.get_todays_log_content()

# Check connectivity
last_update_delta = time.time() - state.get("timestamp", 0)
is_online = last_update_delta < 120

# 2. STATUS INDICATORS (Top Row)
col1, col2, col3, col4 = st.columns([2, 2, 2, 2])

with col1:
    st.metric("💰 Cash Bestand", f"{state.get('balance', 0):.2f} €")

with col2:
    status_phase = state.get('phase', 'Offline')
    if not is_online:
        st.metric("Status", "OFFLINE 💀", delta_color="inverse")
    elif command == "stop":
        st.metric("Status", "PAUSIERT ⏸️", delta="Stop User", delta_color="off")
    elif "Warten" in status_phase:
        st.metric("Status", "SCHLÄFT 💤", help=state.get('details'))
    elif "Fehler" in status_phase:
        st.metric("Status", "FEHLER ❌", state.get('details'), delta_color="inverse")
    else:
        st.metric("Status", "ARBEITET 🚀", status_phase, delta_color="normal")

with col3:
    # Heartbeat Indicator
    if is_online:
        st.success(f"Online (Last signal: {int(last_update_delta)}s)")
    else:
        st.error(f"Disconnected ({int(last_update_delta)}s)")

with col4:
    # Controls
    if command == "run":
        if st.button("⏸️ PAUSIEREN", type="secondary"):
            remote_manager.set_command("stop")
            st.rerun()
    else:
        if st.button("▶️ STARTEN", type="primary"):
            remote_manager.set_command("run")
            st.rerun()

# 3. DETAILED INFO AREA
st.markdown("---")

tab1, tab2 = st.tabs(["🖥️ Live Konsole", "📝 Transaktions-Historie (Heute)"])

with tab1:
    st.caption(f"Zeigt die rohe Ausgabe des Bots (stdout). Letzte Aktualisierung: {time.strftime('%H:%M:%S')}")
    # We display the log in a code block inside a container to simulate a terminal
    st.markdown(f'<div class="console-box">{live_logs}</div>', unsafe_allow_html=True)
    
    col_r1, col_r2 = st.columns([1, 6])
    with col_r1:
        if st.button("🔄 Refresh"):
            st.rerun()
    with col_r2:
        if st.checkbox("Auto-Refresh (2s)", value=True):
            time.sleep(REFRESH_RATE)
            st.rerun()

with tab2:
    st.info("Hier werden nur erfolgreiche Käufe/Verkäufe gelistet, die in `logs/` gespeichert wurden.")
    st.text_area("", daily_logs, height=400)
    if st.button("Reload Transaction Logs"):
        st.rerun()

# Footer info
st.markdown("---")
st.caption(f"Current Phase Detail: **{state.get('details', 'N/A')}**")