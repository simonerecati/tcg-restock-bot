import json, os, re
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from bs4 import BeautifulSoup

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/139.0 Safari/537.36"

def load(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default

def save(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def get(url):
    req = Request(url, headers={"User-Agent": UA, "Accept-Language": "it-IT,it;q=0.9,en;q=0.8"})
    with urlopen(req, timeout=25) as r:
        return r.read().decode(r.headers.get_content_charset() or "utf-8", errors="replace")

def parse_gamelife(html):
    soup = BeautifulSoup(html, "html.parser")
    text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))
    title = soup.find("h1")
    title = title.get_text(" ", strip=True) if title else (soup.title.get_text(" ", strip=True) if soup.title else "")
    price = ""
    el = soup.select_one('meta[itemprop="price"], meta[property="product:price:amount"], [itemprop="price"]')
    if el:
        price = el.get("content") or el.get_text(" ", strip=True)
    if not price:
        m = re.search(r"(\d{1,4}(?:[.,]\d{2})?)\s*€", text)
        price = (m.group(1) + " €") if m else "n/d"
    sold = bool(re.search(r"\bEsaurito\b|\bFuori stock\b|\bNon disponibile\b", text, re.I))
    cart = bool(re.search(r"Aggiungi al carrello|Add to cart", text, re.I))
    available = cart and not sold
    return available, title, price

def tg(method, data=None):
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    body = urlencode(data or {}).encode()
    req = Request(url, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())

def chat_id():
    result = tg("getUpdates", {"timeout": 1})
    for u in reversed(result.get("result", [])):
        m = u.get("message") or u.get("edited_message")
        if m and m.get("chat", {}).get("type") == "private":
            return m["chat"]["id"]
    return None

def alert(cid, name, url, price):
    tg("sendMessage", {"chat_id": cid, "text": f"🚨 RESTOCK RILEVATO!\n\n📦 {name}\n💰 {price}\n🟢 DISPONIBILE\n\n👉 {url}"})

def main():
    products = load("products.json", [])
    state = load("state.json", {})
    cid = chat_id()
    if not products:
        print("Nessun prodotto configurato.")
        return
    for p in products:
        pid, url, name = p["id"], p["url"], p["name"]
        try:
            if "gamelife.it" not in url.lower():
                raise RuntimeError("Parser attualmente configurato per Gamelife.")
            available, title, price = parse_gamelife(get(url))
            old = state.get(pid, {}).get("available", False)
            print(f"{pid}: {'DISPONIBILE' if available else 'NON DISPONIBILE'}")
            if not old and available and cid is not None:
                alert(cid, name, url, price)
            state[pid] = {"available": available, "price": price, "title": title,
                           "checked_at": datetime.now(timezone.utc).isoformat()}
        except Exception as e:
            print(f"{pid}: ERRORE - {e}")
            state[pid] = {**state.get(pid, {}), "error": str(e)[:500],
                          "checked_at": datetime.now(timezone.utc).isoformat()}
    save("state.json", state)

if __name__ == "__main__":
    main()
