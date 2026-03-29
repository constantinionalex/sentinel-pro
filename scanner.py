import asyncio
import aiohttp
import pandas as pd
import redis
import time

r = redis.Redis(host="redis", port=6379, decode_responses=True)

# --- LISTĂ SIMBOLURI ---
def get_symbols():
    df1 = pd.read_csv("https://raw.githubusercontent.com/datasets/nasdaq-listings/master/data/nasdaq-listed-symbols.csv")
    df2 = pd.read_csv("https://raw.githubusercontent.com/datasets/nyse-listed/master/data/nyse-listed.csv")

    symbols = list(df1['Symbol'].dropna()) + list(df2['ACT Symbol'].dropna())
    return list(set(symbols))[:3000]


# --- FETCH ---
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

            df = pd.DataFrame({
                "Close": close,
                "Volume": volume
            }).dropna()

            return symbol, df

    except:
        return None


# --- SCOR ---
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

    return {
        "price": round(p,2),
        "score": score,
        "vol": round(vol_r,2),
        "change": round(change*100,1)
    }


# --- AUTOTRADER LOGIC ---
last_alert = {}

def should_alert(symbol):
    now = time.time()
    if symbol not in last_alert or now - last_alert[symbol] > 3600:
        last_alert[symbol] = now
        return True
    return False


def auto_trader(symbol, data):
    # salvăm top oportunități
    if data["score"] >= 4:
        r.hset("auto_trades", symbol, str(data))

    # ALERTĂ DOAR ELITE
    if data["score"] >= 5 and should_alert(symbol):
        msg = f"""🚀 AUTO TRADE SIGNAL
{symbol}
Score: {data['score']}
Price: {data['price']}$
Vol: {data['vol']}x
Change: {data['change']}%
"""
        r.lpush("telegram_queue", msg)


# --- WORKER ---
async def worker(symbols):
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


# --- LOOP ---
async def main():
    symbols = get_symbols()

    BATCH = 100

    while True:
        for i in range(0, len(symbols), BATCH):
            batch = symbols[i:i+BATCH]
            await worker(batch)

        await asyncio.sleep(30)


asyncio.run(main())
