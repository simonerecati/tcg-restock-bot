import json
import os
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


BASE_DIR = Path(__file__).resolve().parent
PRODUCTS_FILE = BASE_DIR / "products.json"
STATE_FILE = BASE_DIR / "state.json"

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")


def load_json(path, default):
    if not path.exists():
        return default

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def telegram_request(method, payload=None):
    import urllib.request

    url = f"https://api.telegram.org/bot{TOKEN}/{method}"

    if payload is None:
        with urllib.request.urlopen(url, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def get_chat_id():
    try:
        data = telegram_request("getUpdates")

        for update in reversed(data.get("result", [])):
            message = update.get("message")

            if message and message.get("chat", {}).get("type") == "private":
                return message["chat"]["id"]

    except Exception as e:
        print(f"Errore Telegram: {e}")

    return None


def send_telegram(chat_id, text):
    telegram_request(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": False,
        },
    )


def check_product(page, product):
    print(f"\nControllo: {product['name']}")
    print(product["url"])

    page.goto(
        product["url"],
        wait_until="domcontentloaded",
        timeout=60000,
    )

    page.wait_for_timeout(3000)

    soup = BeautifulSoup(page.content(), "html.parser")
    text = soup.get_text(" ", strip=True).lower()

    sold_out = any(
        phrase in text
        for phrase in [
            "esaurito",
            "fuori stock",
            "non disponibile",
        ]
    )

    buy_available = any(
        phrase in text
        for phrase in [
            "aggiungi al carrello",
            "add to cart",
        ]
    )

    available = buy_available and not sold_out

    print(f"Esaurito: {sold_out}")
    print(f"Acquistabile: {buy_available}")
    print(f"DISPONIBILE: {available}")

    return available


def main():
    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN non configurato")

    products = load_json(PRODUCTS_FILE, [])
    state = load_json(STATE_FILE, {})

    chat_id = get_chat_id()

    if not chat_id:
        print("Nessuna chat Telegram trovata.")
        print("Invia /start al bot e riprova.")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        page = browser.new_page(
            viewport={"width": 1366, "height": 768},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        )

        for product in products:
            product_id = product["id"]

            try:
                available = check_product(page, product)
                previous = state.get(product_id, False)

                if available and not previous:
                    message = (
                        "🚨 RESTOCK RILEVATO!\n\n"
                        f"📦 {product['name']}\n"
                        "🟢 DISPONIBILE\n\n"
                        f"👉 {product['url']}"
                    )

                    send_telegram(chat_id, message)
                    print("🚨 ALERT INVIATO!")

                state[product_id] = available

            except Exception as e:
                print(f"❌ Errore durante il controllo: {e}")

        browser.close()

    save_json(STATE_FILE, state)


if __name__ == "__main__":
    main()
