import streamlit as st
import pandas as pd
import requests
import os
import time
import logging

# =====================
# Configurare logging
# =====================
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# =====================
# Configurări TwelveData
# =====================
TD_API_KEY = os.getenv("TD_API_KEY")
if not TD_API_KEY:
    TD_API_KEY = "0eef54e01c5b4f6aa18c054d569084de"  # fallback

SYMBOLS_FILE = "symbols.txt"  # fișierul cu cele 7000 simboluri

# =====================
# Funcții helper
# =====================
def fetch_price(symbol):
    """Preia prețul curent de la TwelveData"""
    url = f"https://api.twelvedata.com/price?symbol={symbol}&apikey={TD_API_KEY}"
    try:
        resp = requests.get(url, timeout=10).json()
        if "price" in resp:
            return float(resp["price"])
        else:
            logger.warning(f"⚠️ Eroare la {symbol}: {resp.get('message', 'No price')}")
            return None
    except Exception as e:
        logger.warning(f"⚠️ Eroare la {symbol}: {str(e)}")
        return None

def load_symbols():
    if os.path.exists(SYMBOLS_FILE):
        with open(SYMBOLS_FILE, "r") as f:
            return [line.strip() for line in f if line.strip()]
    return []

# =====================
# Streamlit UI
# =====================
st.set_page_config(page_title="Sentinel Scanner", layout="wide")
st.title("📈 Sentinel Scanner v3 (TwelveData)")

tab_scaner, tab_portofoliu = st.tabs(["Scaner", "Portofoliu"])

# =====================
# TAB SCANER
# =====================
with tab_scaner:
    st.subheader("🔹 Scanare simboluri")
    symbols = load_symbols()
    scan_limit = st.number_input("Număr simboluri de scanat simultan:", min_value=1, max_value=100, value=20)
    if st.button("Începe scanarea"):
        progress_text = st.empty()
        for i, sym in enumerate(symbols[:scan_limit], 1):
            price = fetch_price(sym)
            if price is not None:
                st.write(f"{i}/{scan_limit} 🔹 {sym} → {price}")
            else:
                st.warning(f"{i}/{scan_limit} ⚠️ {sym} - eroare la preluarea prețului")
            progress_text.text(f"Scanate {i}/{scan_limit} simboluri")
            time.sleep(0.5)  # pauză ca să nu dăm rate-limit

# =====================
# TAB PORTOFOLIU
# =====================
with tab_portofoliu:
    st.subheader("💼 Portofoliu personal")
    
    # Inițializare sesiune
    if "portfolio" not in st.session_state:
        st.session_state.portfolio = []

    # Adăugare simbol
    add_symbol = st.text_input("Adaugă simbol nou:")
    if st.button("Adaugă la portofoliu") and add_symbol:
        if add_symbol not in st.session_state.portfolio:
            st.session_state.portfolio.append(add_symbol.upper())
        else:
            st.warning(f"{add_symbol} există deja în portofoliu!")

    # Afișare portofoliu cu opțiune de ștergere individuală
    if st.session_state.portfolio:
        st.write("### Simboluri în portofoliu:")
        for sym in st.session_state.portfolio[:]:
            col1, col2 = st.columns([4,1])
            col1.write(sym)
            if col2.button("❌ Șterge", key=sym):
                st.session_state.portfolio.remove(sym)
                st.experimental_rerun()  # actualizează lista după ștergere
    else:
        st.info("Portofoliul este gol.")

# =====================
# Log session info
# =====================
st.sidebar.subheader("ℹ️ Info")
st.sidebar.write(f"Simboluri disponibile: {len(symbols)}")
st.sidebar.write(f"Simboluri în portofoliu: {len(st.session_state.portfolio)}")
