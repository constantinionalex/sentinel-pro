import yfinance as yf
import pandas as pd
import time
import redis
from concurrent.futures import ThreadPoolExecutor

r = redis.Redis(host="redis", port=6379, decode_responses=True)

symbols = ["AAPL","MSFT","NVDA","TSLA","AMZN","META","AMD"]

def analyze(s):
    try:
        d = yf.download(s, period="1d", interval="5m", progress=False)
        if d.empty:
            return

        price = d["Close"].iloc[-1]
        vol = d["Volume"].iloc[-1]
        vavg = d["Volume"].rolling(30).mean().iloc[-1]

        vol_r = vol / vavg if vavg > 0 else 0

        r.hset("market", s, str({
            "symbol": s,
            "price": round(price,2),
            "vol": round(vol_r,2)
        }))
    except:
        pass

def run():
    while True:
        with ThreadPoolExecutor(max_workers=5) as ex:
            ex.map(analyze, symbols)
        time.sleep(30)

run()
