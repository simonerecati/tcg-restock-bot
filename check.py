import json
import os
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup


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


def get_page(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/131.0 Safari/537.36"
            )
        },
    )

    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read()


def get_chat_id():
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"

    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))

        for update in reversed(data.get("result", [])):
            message = update.get("message")

            if message and message.get("chat", {}).get("type") == "private":
                return message["chat"]["id"]

    except Exception as e:
        print(f"Errore Telegram getUpdates: {e}")

    return None


def send_telegram(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    payload = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": False
    }).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        print(response.read().decode("utf-8"))


def check_product(product):
    print(f"\nControllo: {product['name']}")
    print(product["url"])

    html = get_page(product["url"])
    soup = BeautifulSoup(html, "html.parser")

    text = soup.get_text(" ", strip=True).lower()

    # Stato chiaramente esaurito
    sold_out = any(
        phrase in text
        for phrase in [
            "esaurito",
            "fuori stock",
            "non disponibile",
        ]
    )

    # Pulsanti/azioni che indicano acquisto effettivo
    buy_available = any(
        phrase in text
        for phrase in [
            "aggiungi al carrello",
            "add to cart",
        ]
    )

    # Per i preorder Gamelife non consideriamo sufficiente
    # la semplice parola "prenota", perché può comparire
    # anche nel riepilogo di prodotti non ancora prenotabili.
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

    for product in products:
        product_id = product["id"]

        try:
            available = check_product(product)
            previous = state.get(product_id, False)

            # Alert SOLO quando passa da non disponibile a disponibile
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

    save_json(STATE_FILE, state)


if __name__ == "__main__":
    main()
