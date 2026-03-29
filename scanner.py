import asyncio
import aiohttp
import pandas as pd
import redis
import time
import os

TD_API_KEY = os.getenv("TD_API_KEY")

r = redis.Redis(host=os.getenv("REDIS_HOST","redis"), port=int(os.getenv("REDIS_PORT",6379)), decode_responses=True)

# --- LISTA SIMBOLURILOR ---
def get_symbols():
    if os.path.exists("symbols.txt"):
        with open("symbols.txt") as f:
            return [line.strip() for line in f if line.strip()]
    # fallback: câteva simboluri
    return ["AAPL","MSFT","NVDA","TSLA","AMZN","GOOGL","META","AMD","INTC"]

# --- FETCH DATA TWELVEDATA ---
async def fetch_td(session, symbol):
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": "5min",
        "outputsize": 96,
        "apikey": TD_API_KEY
    }
    try:
        async with session.get(url, params=params, timeout=10) as resp:
            data = await resp.json()
            if data.get("status") == "error":
                print(f"⚠️ TD error for {symbol}: {data.get('message')}")
                return None
            df = pd.DataFrame(data.get("values", []))
            if df.empty:
                return None
            df = df.sort_values("datetime")
            df["close"] = pd.to_numeric(df["close"], errors="coerce")
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
            df = df.dropna(subset=["close","volume"])
            return symbol, df
    except Exception as e:
        print(f"⚠️ Fetch TD failed {symbol}: {e}")
        return None

# --- CALCULEAZA SCORUL PENTRU AUTO-TRADER ---
def compute_score(df):
    if len(df) < 20:
        return None
    p = df["close"].iloc[-1]
    ema = df["close"].ewm(span=20).mean().iloc[-1]
    vol = df["volume"].iloc[-1]
    vavg = df["volume"].rolling(20).mean().iloc[-1]
    vol_r = vol / vavg if vavg > 0 else 0
    change = (p / df["close"].iloc[0]) - 1

    score = 0
    if vol_r > 2.5: score += 2
    if p > ema: score += 1
    if 0.04 < change < 0.12: score += 2
    return {"price": round(p,2), "score": score, "vol": round(vol_r,2), "change": round(change*100,1)}

last_alert = {}
def should_alert(symbol):
    now = time.time()
    if symbol not in last_alert or now - last_alert[symbol] > 3600:  # alert max o data/ora
        last_alert[symbol] = now
        return True
    return False

# --- AUTO-TRADER LOGIC ---
def auto_trader(symbol, data):
    if data["score"] >= 4:
        r.hset("auto_trades", symbol, str(data))
    if data["score"] >= 5 and should_alert(symbol):
        msg = f"🚀 AUTO TRADE SIGNAL\n{symbol}\nScore: {data['score']}\nPrice: {data['price']}$\n"
        r.lpush("telegram_queue", msg)
        print(f"🔔 Telegram queued for {symbol}")

# --- WORKER ASYNC ---
async def worker(symbols):
    print(f"Scanning batch {len(symbols)}")
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_td(session, s) for s in symbols]
        results = await asyncio.gather(*tasks)
        for res in results:
            if not res: continue
            symbol, df = res
            data = compute_score(df)
            if not data: continue
            r.hset("market", symbol, str(data))
            auto_trader(symbol, data)
            print(f"{symbol} -> score {data['score']}")

# --- MAIN LOOP ---
async def main():
    print("🚀 Scanner started (TwelveData)")
    symbols = get_symbols()
    BATCH = 50
    while True:
        for i in range(0, len(symbols), BATCH):
            batch = symbols[i:i+BATCH]
            await worker(batch)
            await asyncio.sleep(1)  # stay under free API rate limit
        await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main())
