import asyncio
import aiohttp
import pandas as pd
import redis
import time

r = redis.Redis(host="redis", port=6379, decode_responses=True)

def get_symbols():
    try:
        df1 = pd.read_csv("https://raw.githubusercontent.com/datasets/nasdaq-listings/master/data/nasdaq-listed-symbols.csv")
        symbols1 = list(df1['Symbol'].dropna())
    except Exception as e:
        print("⚠️ NASDAQ symbols load failed:", e)
        symbols1 = []

    try:
        df2 = pd.read_csv("https://raw.githubusercontent.com/plotly/datasets/master/stockdata2.csv")
        symbols2 = list(df2.columns)
    except Exception as e:
        print("⚠️ NYSE symbols load failed:", e)
        symbols2 = []

    symbols = list(set(symbols1 + symbols2))
    symbols = [s for s in symbols if isinstance(s, str) and len(s) <= 5]
    print(f"✅ Loaded {len(symbols)} symbols")
    return symbols[:3000]

async def fetch(session, symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=5m&range=1d"
    try:
        async with session.get(url, timeout=5) as resp:
            data = await resp.json()
            result = data.get("chart", {}).get("result")
            if not result:
                return None
            q = result[0]["indicators"]["quote"][0]
            close = q["close"]
            volume = q["volume"]
            if not close or not volume:
                return None
            df = pd.DataFrame({"Close": close, "Volume": volume}).dropna()
            return symbol, df
    except Exception as e:
        print(f"⚠️ Fetch failed for {symbol}: {e}")
        return None

def compute_score(df):
    if len(df) < 30:
        return None
    p = df['Close'].iloc[-1]
    ema = df['Close'].ewm(span=20).mean().iloc[-1]
    vol = df['Volume'].iloc[-1]
    vavg = df['Volume'].rolling(20).mean().iloc[-1]
    vol_r = vol / vavg if vavg > 0 else 0
    change = (p / df['Close'].iloc[-15]) - 1
    score = 0
    if vol_r > 2.5: score += 2
    if p > ema: score += 1
    if 0.04 < change < 0.12: score += 2
    return {"price": round(p,2), "score": score, "vol": round(vol_r,2), "change": round(change*100,1)}

last_alert = {}

def should_alert(symbol):
    now = time.time()
    if symbol not in last_alert or now - last_alert[symbol] > 3600:
        last_alert[symbol] = now
        return True
    return False

def auto_trader(symbol, data):
    if data["score"] >= 4:
        r.hset("auto_trades", symbol, str(data))
    if data["score"] >= 5 and should_alert(symbol):
        msg = f"""🚀 AUTO TRADE SIGNAL
{symbol}
Score: {data['score']}
Price: {data['price']}$
Vol: {data['vol']}x
Change: {data['change']}%
"""
        r.lpush("telegram_queue", msg)
        print(f"🔔 Telegram queued for {symbol}")

async def worker(symbols):
    print(f"🔎 Scanning batch: {len(symbols)} symbols")
    async with aiohttp.ClientSession() as session:
        tasks = [fetch(session, s) for s in symbols]
        results = await asyncio.gather(*tasks)
        for res in results:
            if not res:
                continue
            symbol, df = res
            data = compute_score(df)
            if not data:
                continue
            r.hset("market", symbol, str(data))
            auto_trader(symbol, data)
            print(f"✅ {symbol} -> score {data['score']}")

async def main():
    print("🚀 Scanner started")
    symbols = get_symbols()
    BATCH = 100
    while True:
        print("🔁 New scan cycle")
        for i in range(0, len(symbols), BATCH):
            batch = symbols[i:i+BATCH]
            await worker(batch)
        await asyncio.sleep(30)

asyncio.run(main())
