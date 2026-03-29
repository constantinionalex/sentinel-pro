import os
import time
import threading
from datetime import datetime
import pandas as pd
import requests
import redis
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from streamlit.runtime.scriptrunner import add_script_run_ctx

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
    if df[(df['date']==day) & (df['symbol']==symbol) & (df['type']==type_)].empty:
        pd.concat([df, pd.DataFrame([{"date": day, "symbol": symbol, "type": type_}])]).to_csv(f, index=False)
        return True
    return False

REDIS_HOST = os.getenv("REDIS_HOST","localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT",6379))
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

if not os.path.exists("p.csv"):
    df_p = pd.DataFrame([{"Simbol":"AAPL","Pret_A":140,"Pret_C":150,"Varf_24h":155},{"Simbol":"MSFT","Pret_A":310,"Pret_C":300,"Varf_24h":315}])
    df_p.to_csv("p.csv", index=False)

if not os.path.exists("analysis.csv"):
    df_a = pd.DataFrame([{"Simbol":"AAPL","Pret":150,"Vol_Relativ":"1.2x","Diff_24h":"+2%","Burst":"NU","Ora":"10:00"},
                         {"Simbol":"MSFT","Pret":300,"Vol_Relativ":"0.8x","Diff_24h":"-1%","Burst":"NU","Ora":"10:00"}])
    df_a.to_csv("analysis.csv", index=False)

@st.cache_data
def list_nasdaq():
    return ["AAPL","MSFT","NVDA","TSLA","AMZN","GOOGL","META","AVGO","COST","PEP","ADBE","CSCO","TMUS","CMCSA","INTC","AMD","QCOM"]

def run_portfolio():
    pf = "p.csv"
    while True:
        df = pd.read_csv(pf)
        for i,rw in df.iterrows():
            try:
                t = pd.read_json(f"https://api.twelvedata.com/price?symbol={rw['Simbol']}&apikey={os.getenv('TD_API_KEY')}")
                c_p = float(t["price"])
                v_24 = c_p*1.05
                if c_p < rw['Pret_A']*0.95 and log_alert(rw['Simbol'], "DROP_A"):
                    send_tg(f"⚠️ {rw['Simbol']} sub -5% achizitie: {round(c_p,2)}$")
                if c_p < v_24*0.85 and log_alert(rw['Simbol'], "DROP_V"):
                    send_tg(f"⚠️ {rw['Simbol']} sub -15% varf: {round(c_p,2)}$")
                df.at[i,'Pret_C'] = round(c_p,2)
                df.at[i,'Varf_24h'] = round(v_24,2)
            except: pass
        df.to_csv(pf,index=False)
        time.sleep(300)

if 'init' not in st.session_state:
    t1 = threading.Thread(target=run_portfolio, daemon=True)
    add_script_run_ctx(t1)
    t1.start()
    st.session_state['init'] = True

st.title("🛡️ Sentinel Market Tracker")
tab1,tab2,tab3 = st.tabs(["💼 Portofoliu","🎯 Screening Burst","📊 Analiza Detaliată"])
with tab1:
    df_p = pd.read_csv("p.csv")
    with st.form("add"):
        c1,c2 = st.columns(2)
        s_in = c1.selectbox("Simbol:",list_nasdaq())
        p_in = c2.number_input("Preț Achiziție ($):")
        if st.form_submit_button("Adaugă"):
            pd.concat([df_p, pd.DataFrame([{'Simbol':s_in,'Pret_A':p_in,'Pret_C':0,'Varf_24h':0}])]).to_csv("p.csv", index=False)
            st.experimental_rerun()
    st.table(df_p)
    if st.button("Reset Portofoliu"):
        os.remove("p.csv")
        st.experimental_rerun()
with tab2:
    if os.path.exists("analysis.csv"):
        df_a = pd.read_csv("analysis.csv")
        st.dataframe(df_a[df_a['Burst']=="DA"], use_container_width=True)
with tab3:
    if os.path.exists("analysis.csv"):
        st.dataframe(pd.read_csv("analysis.csv"), use_container_width=True)
