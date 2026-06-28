import os
import json
import hashlib
import feedparser
import requests
from datetime import datetime, timezone, timedelta

DATA_FILE = "data/news.json"
CONFIG_FILE = "config.json"


def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_news():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_news(news):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(news, f, ensure_ascii=False, indent=2)


def make_id(text):
    return hashlib.md5(text.encode()).hexdigest()[:12]


def fetch_rss_feeds():
    """Pull headlines from public RSS feeds (no auth required)."""
    feeds = [
        ("Cointelegraph Base", "https://cointelegraph.com/rss/tag/base"),
        ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
        ("The Defiant", "https://thedefiant.io/feed"),
        ("BlockWorks", "https://blockworks.co/feed"),
        ("CryptoSlate", "https://cryptoslate.com/feed/"),
        ("Decrypt", "https://decrypt.co/feed"),
        ("Bankless", "https://www.bankless.com/feed"),
    ]
    out = []
    now = datetime.now(timezone.utc).isoformat()
    for name, url in feeds:
        try:
            feed = feedparser.parse(url)
            count = 0
            for entry in feed.entries[:15]:
                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                if not title or not link:
                    continue
                out.append({
                    "id": f"rss_{make_id(link)}",
                    "source": name,
                    "title": title,
                    "url": link,
                    "published_at": entry.get("published", ""),
                    "fetched_at": now,
                    "used": False,
                })
                count += 1
            print(f"  {name}: {count} items")
        except Exception as e:
            print(f"  {name} error: {e}")
    return out


def fetch_defillama():
    """Fetch Base chain TVL from DeFiLlama (no key required)."""
    try:
        r = requests.get("https://api.llama.fi/v2/chains", timeout=15)
        r.raise_for_status()
        base = next((c for c in r.json() if c.get("name", "").lower() == "base"), None)
        if not base:
            return []
        tvl = base.get("tvl", 0)
        change = base.get("change_1d", 0) or 0
        emoji = "🟢" if change >= 0 else "🔴"
        return [{
            "id": f"llama_{datetime.now(timezone.utc).strftime('%Y%m%d%H')}",
            "source": "DeFiLlama",
            "title": f"Base TVL: ${tvl:,.0f} {emoji} {change:+.2f}% (24h)",
            "url": "https://defillama.com/chain/Base",
            "published_at": "",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "used": False,
        }]
    except Exception as e:
        print(f"DeFiLlama error: {e}")
    return []


def filter_news(items, keywords):
    kw = [k.lower() for k in keywords]
    return [i for i in items
            if any(k in (i["title"] + " " + i["url"]).lower() for k in kw)]


def main():
    config = load_config()
    keywords = config.get("filter_keywords", [])

    existing = load_news()
    existing_ids = {i["id"] for i in existing}

    print("Fetching news...")
    fresh = []
    fresh.extend(fetch_rss_feeds())
    fresh.extend(fetch_defillama())

    filtered = filter_news(fresh, keywords)

    added = 0
    for item in filtered:
        if item["id"] not in existing_ids:
            existing.append(item)
            added += 1

    # Drop items older than 7 days
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    existing = [
        i for i in existing
        if not i.get("fetched_at")
        or datetime.fromisoformat(i["fetched_at"].replace("Z", "+00:00")) > cutoff
    ]

    save_news(existing)
    print(f"Added {added} new items, total in storage: {len(existing)}")


if __name__ == "__main__":
    main()
