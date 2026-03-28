# app.py
import os
import time
import threading
from datetime import datetime

import pandas as pd
import yfinance as yf
import requests
import redis
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from streamlit.runtime.scriptrunner import add_script_run_ctx

# --- CONFIG STREAMLIT ---
st.set_page_config(layout="wide", page_title="Sentinel Pro")
st_autorefresh(interval=20000, key="refresh")

# --- TELEGRAM ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def send_tg(msg):
    try:
        if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
            requests.get(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={msg}",
                timeout=5
            )
    except:
        pass


def log_alert(symbol, type_):
    f, day = "alert_log.csv", datetime.now().strftime("%Y-%m-%d")
    if not os.path.exists(f):
        pd.DataFrame(columns=["date", "symbol", "type"]).to_csv(f, index=False)
    df = pd.read_csv(f)
    if df[(df['date'] == day) & (df['symbol'] == symbol) & (df['type'] == type_)].empty:
        pd.concat([df, pd.DataFrame([{"date": day, "symbol": symbol, "type": type_}])]).to_csv(f, index=False)
        return True
    return False


# --- REDIS CONNECTION ---
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# --- CREARE CSV-URI INITIALE ---
if not os.path.exists("p.csv"):
    df_p = pd.DataFrame([
        {"Simbol": "AAPL", "Pret_A": 140, "Pret_C": 150, "Varf_24h": 155},
        {"Simbol": "MSFT", "Pret_A": 310, "Pret_C": 300, "Varf_24h": 315}
    ])
    df_p.to_csv("p.csv", index=False)

if not os.path.exists("analysis.csv"):
    df_a = pd.DataFrame([
        {"Simbol": "AAPL", "Pret": 150, "Vol_Relativ": "1.2x", "Diff_24h": "+2%", "Burst": "NU", "Ora": "10:00"},
        {"Simbol": "MSFT", "Pret": 300, "Vol_Relativ": "0.8x", "Diff_24h": "-1%", "Burst": "NU", "Ora": "10:00"}
    ])
    df_a.to_csv("analysis.csv", index=False)


# --- NASDAQ SYMBOLS ---
@st.cache_data
def list_nasdaq():
    return ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "GOOGL", "META", "AVGO",
            "COST", "PEP", "ADBE", "CSCO", "TMUS", "CMCSA", "INTC", "AMD", "QCOM"]


# --- MOTOR SCANARE ---
def run_scanner():
    f = "analysis.csv"
    cols = ["Simbol", "Pret", "Vol_Relativ", "Diff_24h", "Burst", "Ora"]
    if not os.path.exists(f):
        pd.DataFrame(columns=cols).to_csv(f, index=False)

    symbols = list_nasdaq()
    while True:
        for s in symbols:
            try:
                d_5m = yf.download(s, period="1d", interval="5m", progress=False)
                d_1h = yf.download(s, period="2d", interval="60m", progress=False)

                if not d_5m.empty and not d_1h.empty:
                    p_now = float(d_5m['Close'].iloc[-1])
                    v_now = float(d_5m['Volume'].iloc[-1])
                    v_avg = d_5m['Volume'].rolling(50).mean().iloc[-1]
                    p_avg_24 = d_1h['Close'].tail(24).mean()

                    vol_r = v_now / v_avg if v_avg > 0 else 0
                    p_diff = (p_now / p_avg_24) - 1
                    burst = vol_r > 2.0 and p_diff > 0.10

                    if burst and log_alert(s, "BURST"):
                        send_tg(f"🚀 BURST: {s} @ {round(p_now,2)}$ (+{round(p_diff*100,1)}%)")

                    df = pd.read_csv(f)
                    row = {"Simbol": s, "Pret": round(p_now, 2), "Vol_Relativ": f"{round(vol_r,1)}x",
                           "Diff_24h": f"{round(p_diff*100,1)}%", "Burst": "DA" if burst else "NU",
                           "Ora": datetime.now().strftime("%H:%M")}
                    df = pd.concat([df[df['Simbol'] != s], pd.DataFrame([row])])
                    df.to_csv(f, index=False)
                time.sleep(1)
            except:
                continue


# --- MONITORIZARE PORTOFOLIU ---
def run_portfolio():
    pf = "p.csv"
    if not os.path.exists(pf):
        pd.DataFrame(columns=['Simbol', 'Pret_A', 'Pret_C', 'Varf_24h']).to_csv(pf, index=False)

    while True:
        df = pd.read_csv(pf)
        for i, r in df.iterrows():
            try:
                t = yf.Ticker(r['Simbol']).history(period="1d", interval="15m")
                if not t.empty:
                    c_p = t['Close'].iloc[-1]
                    v_24 = t['High'].max()

                    if c_p < r['Pret_A'] * 0.95 and log_alert(r['Simbol'], "DROP_A"):
                        send_tg(f"⚠️ {r['Simbol']} sub -5% achizitie: {round(c_p,2)}$")

                    if c_p < v_24 * 0.85 and log_alert(r['Simbol'], "DROP_V"):
                        send_tg(f"⚠️ {r['Simbol']} sub -15% varf: {round(c_p,2)}$")

                    df.at[i, 'Pret_C'] = round(c_p, 2)
                    df.at[i, 'Varf_24h'] = round(v_24, 2)
            except:
                pass
        df.to_csv(pf, index=False)
        time.sleep(300)


# --- START THREAD-URI ODATA CU STREAMLIT ---
if 'init' not in st.session_state:
    t1 = threading.Thread(target=run_scanner, daemon=True)
    t2 = threading.Thread(target=run_portfolio, daemon=True)
    add_script_run_ctx(t1)
    add_script_run_ctx(t2)
    t1.start()
    t2.start()
    st.session_state['init'] = True


# --- INTERFAȚA STREAMLIT ---
st.title("🛡️ Sentinel Market Tracker")
tab1, tab2, tab3 = st.tabs(["💼 Portofoliu", "🎯 Screening Burst", "📊 Analiza Detaliată"])

with tab1:
    df_p = pd.read_csv("p.csv")
    with st.form("add"):
        c1, c2 = st.columns(2)
        s_in = c1.selectbox("Simbol:", list_nasdaq())
        p_in = c2.number_input("Preț Achiziție ($):")
        if st.form_submit_button("Adaugă"):
            pd.concat([df_p, pd.DataFrame([{'Simbol': s_in, 'Pret_A': p_in, 'Pret_C': 0, 'Varf_24h': 0}])]).to_csv("p.csv", index=False)
            st.experimental_rerun()
    st.table(df_p)
    if st.button("Reset Portofoliu"):
        os.remove("p.csv")
        st.experimental_rerun()

with tab2:
    if os.path.exists("analysis.csv"):
        df_a = pd.read_csv("analysis.csv")
        st.dataframe(df_a[df_a['Burst'] == "DA"], use_container_width=True)

with tab3:
    if os.path.exists("analysis.csv"):
        st.dataframe(pd.read_csv("analysis.csv"), use_container_width=True)
