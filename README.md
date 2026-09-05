# TCG Restock Bot

Controlla Gamelife ogni 5 minuti e invia un alert Telegram quando un prodotto passa da non disponibile a disponibile.

Configurazione:
1. GitHub repository -> Settings -> Secrets and variables -> Actions -> New repository secret.
2. Nome: TELEGRAM_BOT_TOKEN
3. Valore: token di BotFather (non inserirlo mai nei file).
4. Modifica products.json con le URL dei prodotti Gamelife.
5. Avvia una volta manualmente il workflow da Actions.

Il chat ID viene ricavato automaticamente dalla coda Telegram dopo che hai usato /start sul bot.
