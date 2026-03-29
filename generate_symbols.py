import requests
import os
import json

TD_API_KEY = os.getenv("TD_API_KEY")  # setează cheia ta TwelveData în mediul de rulare
OUTPUT_FILE = "symbols.txt"

if not TD_API_KEY:
    raise Exception("0eef54e01c5b4f6aa18c054d569084de")

url = f"https://api.twelvedata.com/stocks?apikey={TD_API_KEY}&exchange=NASDAQ"  # poți adăuga NYSE sau alte exchange-uri

symbols = []

while url:
    resp = requests.get(url, timeout=10)
    data = resp.json()
    if "data" not in data:
        raise Exception(f"Nu s-au putut prelua simbolurile: {data}")
    for item in data["data"]:
        symbols.append(item["symbol"])
    # verifică dacă există paginare
    url = data.get("next_page_url")  # dacă nu există, va fi None

# salvează simbolurile într-un fișier
with open(OUTPUT_FILE, "w") as f:
    for s in symbols:
        f.write(s + "\n")

print(f"✅ {len(symbols)} simboluri au fost salvate în {OUTPUT_FILE}")
