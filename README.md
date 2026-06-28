# 🐻 Letti Meme Bot

> Automated crypto-meme machine for the **Base** network — part of the **LettiVerse** ecosystem 🩵

[![Telegram](https://img.shields.io/badge/Telegram-BaseMemesLetti-2CA5E0?logo=telegram&logoColor=white)](https://t.me/BaseMemesLetti)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Letti Meme Bot** watches the crypto world, hunts for fresh **Base** network news, turns headlines into witty memes using AI, generates images, and ships them straight to Telegram — fully on autopilot.

📢 **Live channel:** [t.me/BaseMemesLetti](https://t.me/BaseMemesLetti)

---

## ✨ Features

- 📰 **News Monitoring** — pulls crypto news from multiple RSS feeds + live on-chain data (Base TVL via DeFiLlama)
- 🧠 **AI Meme Generation** — turns headlines into crypto-native humor (rug, wagmi, gm, ser, anon...)
- 🖼️ **Image Generation** — auto-creates meme art via Pollinations AI (free, no key required)
- 📤 **Auto-Publishing** — posts ready memes with images to a Telegram channel
- 🔁 **No Repeats** — tracks used news so memes never duplicate
- 💸 **Zero Running Cost** — runs free on GitHub Actions + staked CAPU for AI inference

---

## 🏗️ How It Works

The bot runs in **two independent phases**:

### 📰 Phase 1 — News Collector (`fetch_news.py`)
Runs every 30 minutes:
1. Pulls headlines from RSS feeds (Cointelegraph, Decrypt, CoinDesk, and more)
2. Fetches Base chain TVL from DeFiLlama
3. Filters for Base/crypto relevance via keywords
4. Stores fresh items in `data/news.json` (deduplicated)

### 🎨 Phase 2 — Meme Generator (`generate_memes.py`)
Runs 3× daily (09:00 / 15:00 / 21:00 UTC):
1. Reads fresh, unused news
2. AI crafts meme concepts (caption + image prompt)
3. Generates an image from the prompt via Pollinations
4. Posts the meme to Telegram
5. Marks the news item as used

---

## 🛠️ Tech Stack

| Component | Tool |
|-----------|------|
| AI / LLM | OpenCAP Gateway (Claude) |
| Image Generation | Pollinations AI |
| Scheduler | GitHub Actions |
| Delivery | Telegram Bot API |
| News Sources | RSS feeds + DeFiLlama |
| Storage | Git-tracked JSON |

---

## 🚀 Setup

1. **Fork** this repository
2. Create a Telegram bot via [@BotFather](https://t.me/BotFather)
3. Create a channel, add your bot as **admin** with "Post Messages" rights
4. Grab an API key from [Capminal / OpenCAP](https://gw.capminal.ai)
5. Add the following **GitHub Secrets** (`Settings → Secrets and variables → Actions`):

| Secret | Description |
|--------|-------------|
| `OPENCAP_API_KEY` | Your OpenCAP API key |
| `TELEGRAM_BOT_TOKEN` | Bot token from BotFather |
| `TELEGRAM_MEMES_CHAT_ID` | Target channel ID (e.g. `-100...`) |

6. Enable **Actions** and trigger the workflows manually to test

---

## ⚙️ Configuration

Tune everything in `config.json`:

```json
{
  "filter_keywords": ["base", "coinbase", "l2", "defi"],
  "meme_count_per_run": 3,
  "max_news_age_hours": 24
}
