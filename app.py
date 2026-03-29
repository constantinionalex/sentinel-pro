import os
import time
from datetime import datetime

import pandas as pd
import requests
import redis
import streamlit as st
from streamlit_autorefresh import st_autorefresh

st.set_page_config(layout="wide", page_title="Sentinel Pro")
st_autorefresh(interval=20000, key="refresh")

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


REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


# 🔔 TELEGRAM QUEUE
def process_telegram_queue():
    while True:
        msg = r.rpop("telegram_queue")
        if msg:
            send_tg(msg)
        else:
            break

process_telegram_queue()


# --- PORTOFOLIU (NEATINS) ---
if not os.path.exists("p.csv"):
    pd.DataFrame(columns=['Simbol','Pret_A','Pret_C','Varf_24h']).to_csv("p.csv", index=False)


st.title("🛡️ Sentinel Market Tracker")

tab1, tab2 = st.tabs(["💼 Portofoliu", "🤖 AutoTrader"])


# --- PORTOFOLIU ---
with tab1:
    df_p = pd.read_csv("p.csv")

    with st.form("add"):
        c1, c2 = st.columns(2)
        s_in = c1.text_input("Simbol:")
        p_in = c2.number_input("Preț Achiziție ($):")

        if st.form_submit_button("Adaugă"):
            pd.concat([df_p, pd.DataFrame([{
                'Simbol': s_in,
                'Pret_A': p_in,
                'Pret_C': 0,
                'Varf_24h': 0
            }])]).to_csv("p.csv", index=False)
            st.experimental_rerun()

    st.table(df_p)

    if st.button("Reset Portofoliu"):
        os.remove("p.csv")
        st.experimental_rerun()


# --- AUTOTRADER ---
with tab2:
    st.subheader("🔥 Top Oportunități")

    data = r.hgetall("auto_trades")

    rows = []
    for k, v in data.items():
        try:
            d = eval(v)
            d["symbol"] = k
            rows.append(d)
        except:
            pass

    if rows:
        df = pd.DataFrame(rows)
        df = df.sort_values("score", ascending=False)
        df = df[df['score'] >= 4].head(20)

        st.dataframe(df, use_container_width=True)
