import streamlit as st
import redis
import pandas as pd
import ast
import os
import redis

redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", 6379))

r = redis.Redis(host=redis_host, port=redis_port)

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
