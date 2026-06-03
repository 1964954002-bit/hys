# BTC GEX Regime

Low-frequency BTC dealer gamma regime checker using **Deribit public API** (primary source).

## What it tells you

- **Positive net GEX** → dealers tend to dampen moves → range / mean-reversion bias
- **Negative net Gex** → dealers tend to amplify moves → trend / vol-expansion bias

## Setup

```bash
cd ~/Projects/btc-gex-regime
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

Generate a strike x expiry heatmap:

```bash
python main.py --heatmap
python main.py --heatmap --show
python main.py --heatmap --output output/my_heatmap.png
```

Suggested cadence: 2–4 times per day. No API key required.

## Telegram push every 4 hours (GitHub, laptop can sleep)

GitHub runs the script in the cloud on a schedule. Your Mac does not need to stay on.

### 1. Telegram bot (one-time)

1. In Telegram, open **@BotFather** → `/newbot` → save the **bot token**.
2. Open your new bot in Telegram and send any message (e.g. `hi`).
3. In a browser, open (replace `YOUR_TOKEN`):

   `https://api.telegram.org/botYOUR_TOKEN/getUpdates`

4. Find `"chat":{"id":123456789}` — that number is your **chat id**.

If the token was ever pasted in chat or email, use BotFather **`/revoke`** and put only the new token in GitHub Secrets.

### 2. GitHub account and repository (beginner)

1. Sign up at [github.com](https://github.com) (free).
2. Click **+** → **New repository**.
3. Name it e.g. `btc-gex-regime`, leave it **Public** (simplest free Actions), click **Create repository**.
4. GitHub shows “push an existing repository” commands. On your Mac, in the project folder:

```bash
cd ~/Projects/btc-gex-regime
git add .
git commit -m "Add BTC GEX checker and Telegram workflow"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/btc-gex-regime.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your GitHub username. The first `git push` may ask you to log in (browser or token).

### 3. GitHub Secrets (passwords for the workflow)

On the repo page: **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:

| Name | Value |
|------|--------|
| `TELEGRAM_BOT_TOKEN` | token from BotFather |
| `TELEGRAM_CHAT_ID` | numeric chat id |

### 4. Test

**Actions** tab → **Telegram GEX push** → **Run workflow** → **Run workflow**.

In about 1–2 minutes you should get the heatmap on Telegram. After that, it runs automatically every 4 hours (UTC).

### On-demand: send「发图」in Telegram

A second workflow **Telegram on-demand** polls your bot every **3 minutes** (GitHub free tier may delay a bit). When you send any of these in the chat with your bot:

- `发图` / `画图`
- `/chart` / `/push`

it replies「正在生成…」, runs the same pipeline, and sends a fresh heatmap. You do not need to wait for the 4-hour schedule.

**Note:** Only messages from your configured `TELEGRAM_CHAT_ID` are accepted. First push after setup still needs Secrets configured.

### Local test (optional)

```bash
cp .env.example .env
# edit .env with your token and chat id
source .venv/bin/activate
export $(grep -v '^#' .env | xargs)
python scripts/push_telegram.py
python scripts/telegram_listen.py
```

## Notes

- Data source: Deribit options chain (`open_interest`, `mark_iv`, `underlying_price`).
- Greeks are computed with the same Black-Scholes gamma model Deribit uses.
- King Strike = strike with the largest absolute net GEX.
