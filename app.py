import streamlit as st
import redis
import pandas as pd
import ast

r = redis.Redis(host="redis", port=6379, decode_responses=True)

st.set_page_config(layout="wide")
st.title("Sentinel PRO")

data = r.hgetall("market")

rows = []
for v in data.values():
    try:
        rows.append(ast.literal_eval(v))
    except:
        pass

df = pd.DataFrame(rows)

if not df.empty:
    st.dataframe(df, use_container_width=True)
else:
    st.warning("No data yet...")
