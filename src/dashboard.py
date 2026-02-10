import streamlit as st
import remote_manager
import utils
import time
import pandas as pd
import html

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
    .console-box { background-color: #0e0e0e; color: #ffffff; font-family: monospace; padding: 10px; border-radius: 5px; height: 400px; overflow-y: scroll; white-space: pre-wrap; border: 1px solid #444; font-size: 0.85em; }
    div[data-testid="stMetricValue"] { font-size: 28px; }
    /* Fix für Tabellen-Header */
    th { text-align: left !important; }
    </style>
""", unsafe_allow_html=True)

st.title("🤖 OON Trading Bot Controller")

# --- AUTO REFRESH ---
if 'last_run' not in st.session_state:
    st.session_state['last_run'] = time.time()
REFRESH_RATE = 2 

# 1. READ DATA
state = remote_manager.get_state()
command = remote_manager.get_command()
live_logs = remote_manager.get_live_logs(lines=100)

# Check connectivity
last_update_delta = time.time() - state.get("timestamp", 0)
is_online = last_update_delta < 120

# 2. STATUS ROW
col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
with col1:
    st.metric("💰 Cash Bestand", f"{state.get('balance', 0):.2f} €")
with col2:
    status_phase = state.get('phase', 'Offline')
    if not is_online: st.metric("Status", "OFFLINE 💀", delta_color="inverse")
    elif command == "stop": st.metric("Status", "PAUSIERT ⏸️", delta="Stop User", delta_color="off")
    elif "Warten" in status_phase: st.metric("Status", "SCHLÄFT 💤", help=state.get('details'))
    elif "Fehler" in status_phase: st.metric("Status", "FEHLER ❌", state.get('details'), delta_color="inverse")
    else: st.metric("Status", "ARBEITET 🚀", status_phase, delta_color="normal")
with col3:
    if is_online: st.success(f"Online ({int(last_update_delta)}s)")
    else: st.error(f"Disconnected ({int(last_update_delta)}s)")
with col4:
    if command == "run":
        if st.button("⏸️ PAUSIEREN", type="secondary"):
            remote_manager.set_command("stop")
            st.rerun()
    else:
        if st.button("▶️ STARTEN", type="primary"):
            remote_manager.set_command("run")
            st.rerun()

st.markdown("---")

# 3. TABS (Jetzt 3 Tabs)
tab1, tab2, tab3 = st.tabs(["📊 Mein Depot", "📜 Verlauf", "🖥️ Live Konsole"])

# --- TAB 1: DEPOT ---
with tab1:
    st.subheader("Aktienbestand")
    portfolio_data = state.get("portfolio", [])
    
    if portfolio_data:
        df_portfolio = pd.DataFrame(portfolio_data)
        
        rename_map = {
            "name": "Aktie", 
            "qty": "Stk.", 
            "value_eur": "Wert", 
            "performance_since_buy": "Perf.",
            "peak_pct": "Peak%"
        }
        existing_cols = [c for c in rename_map.keys() if c in df_portfolio.columns]
        df_portfolio = df_portfolio[existing_cols].rename(columns=rename_map)

        st.dataframe(
            df_portfolio, 
            width="stretch",
            hide_index=True,
            column_config={
                "Aktie": st.column_config.TextColumn("Aktie", width="large"),
                "Wert": st.column_config.NumberColumn("Wert (€)", format="%.2f €"),
                "Stk.": st.column_config.NumberColumn("Stk.", format="%d"),
                "Peak%": st.column_config.NumberColumn("Peak%", format="%.2f%%"),
            }
        )
    else:
        st.info("Noch keine Depot-Daten verfügbar (Warte auf nächsten Scan).")

    st.subheader("Offene Aufträge")
    orders_data = state.get("open_orders", [])
    if orders_data:
        df_orders = pd.DataFrame(orders_data)
        if not df_orders.empty:
            cols_to_show = ["type", "qty", "name", "status"]
            df_orders = df_orders[[c for c in cols_to_show if c in df_orders.columns]]
            df_orders.rename(columns={"type": "Typ", "qty": "Menge", "name": "Name", "status": "Status"}, inplace=True)
            
            st.dataframe(
                df_orders, 
                width="stretch", 
                hide_index=True,
                column_config={
                    "Name": st.column_config.TextColumn("Name", width="medium"),
                }
            )
    else:
        st.caption("Keine offenen Aufträge.")

# --- TAB 2: VERLAUF (NEU) ---
with tab2:
    st.subheader("Transaktions-Historie")
    history_data = utils.get_transaction_history()
    
    if history_data:
        df_hist = pd.DataFrame(history_data)
        
        st.dataframe(
            df_hist,
            width="stretch",
            hide_index=True,
            column_config={
                "Datum": st.column_config.TextColumn("Datum", width="small"),
                "Zeit": st.column_config.TextColumn("Zeit", width="small"),
                "Aktion": st.column_config.TextColumn("Aktion", width="small"),
                "Name": st.column_config.TextColumn("Name", width="medium"),
                "Menge": st.column_config.NumberColumn("Stk."),
                "Preis": st.column_config.NumberColumn("Kurs (€)", format="%.2f €"),
                "Profit": st.column_config.TextColumn("Profit", width="small"),
                "Grund": st.column_config.TextColumn("KI Begründung", width="large"),
                "ISIN": st.column_config.TextColumn("ISIN", width="small"),
            }
        )
    else:
        st.info("Noch keine Transaktionen in den Logs gefunden.")

# --- TAB 3: KONSOLE ---
with tab3:
    st.caption("Live Output (stdout)")
    # Wir benutzen st.code statt markdown, damit Zeichen wie | oder # nicht als Markdown interpretiert werden
    st.code(live_logs, language="text", wrap_lines=True)
    
    if st.button("Refresh Log"): st.rerun()
    if st.checkbox("Auto-Refresh", value=True):
        time.sleep(REFRESH_RATE)
        st.rerun()