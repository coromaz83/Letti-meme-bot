import os
import json
import sys
import traceback
import urllib.parse
from datetime import datetime, timezone, timedelta

DEBUG_LOG = "data/debug.log"


def log(msg):
    print(msg, flush=True)
    os.makedirs(os.path.dirname(DEBUG_LOG), exist_ok=True)
    with open(DEBUG_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now(timezone.utc).isoformat()}] {msg}\n")


# Reset log on each run
if os.path.exists(DEBUG_LOG):
    os.remove(DEBUG_LOG)

log("=" * 50)
log("=== Letti Meme Bot started ===")

# --- Imports ---
try:
    import requests
    log("requests imported")
except Exception as e:
    log(f"requests error: {e}")
    sys.exit(1)

try:
    import openai
    log(f"openai imported, version: {openai.__version__}")
    from openai import OpenAI
except Exception as e:
    log(f"openai import error: {e}")
    log(traceback.format_exc())
    sys.exit(1)

# --- Secrets ---
TG_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TG_CHAT_ID = os.environ.get("TELEGRAM_MEMES_CHAT_ID", "")
OPENCAP_KEY = os.environ.get("OPENCAP_API_KEY", "")

log(f"TELEGRAM_BOT_TOKEN: {'set' if TG_TOKEN else 'MISSING'}")
log(f"TELEGRAM_MEMES_CHAT_ID: {TG_CHAT_ID or 'MISSING'}")
log(f"OPENCAP_API_KEY: {'set' if OPENCAP_KEY else 'MISSING'}")

if not TG_TOKEN or not TG_CHAT_ID or not OPENCAP_KEY:
    log("Missing secrets — exiting")
    sys.exit(1)

TG_API = f"https://api.telegram.org/bot{TG_TOKEN}"
CONFIG_FILE = "config.json"
DATA_FILE = "data/news.json"

# --- OpenAI client (OpenCAP gateway) ---
log("Creating OpenAI client...")
try:
    ai = OpenAI(
        base_url="https://gw.capminal.ai/api/inference/v1",
        api_key=OPENCAP_KEY,
    )
    log("Client created")
except Exception as e:
    log(f"Client creation error: {e}")
    log(traceback.format_exc())
    sys.exit(1)


def tg_send(text):
    """Send a plain text message to Telegram."""
    log(f"Sending text to Telegram ({len(text)} chars)...")
    if len(text) > 4000:
        text = text[:3997] + "…"
    r = requests.post(f"{TG_API}/sendMessage", json={
        "chat_id": TG_CHAT_ID,
        "text": text,
        "disable_web_page_preview": True,
    })
    log(f"  Telegram status: {r.status_code}")
    if not r.ok:
        log(f"  Telegram response: {r.text[:300]}")
    r.raise_for_status()


def tg_send_photo(image_prompt, caption):
    """Generate an image via Pollinations and send it to Telegram with a caption."""
    enhanced = f"{image_prompt}, meme style, funny, vibrant colors, digital art"
    encoded = urllib.parse.quote(enhanced[:500])
    image_url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width=1024&height=1024&nologo=true"
    )
    log(f"Generating image: {image_url[:80]}...")

    if len(caption) > 1024:
        caption = caption[:1021] + "…"

    r = requests.post(f"{TG_API}/sendPhoto", json={
        "chat_id": TG_CHAT_ID,
        "photo": image_url,
        "caption": caption,
    }, timeout=120)
    log(f"  Telegram status: {r.status_code}")
    if not r.ok:
        log(f"  Telegram response: {r.text[:300]}")
        log("  Falling back to text mode...")
        tg_send(caption + f"\n\n🖼 Image: {image_url}")
        return
    r.raise_for_status()


def load_config():
    if not os.path.exists(CONFIG_FILE):
        log(f"Missing {CONFIG_FILE}")
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_news():
    if not os.path.exists(DATA_FILE):
        log(f"Missing {DATA_FILE}")
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_news(news):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(news, f, ensure_ascii=False, indent=2)


def get_fresh_unused_news(news, max_age_hours):
    """Filter by real publication date, sort newest first."""
    from email.utils import parsedate_to_datetime

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=max_age_hours)
    out = []

    for item in news:
        if item.get("used"):
            continue

        # Try real publication date first
        article_date = None
        pub = item.get("published_at", "")
        if pub:
            try:
                article_date = parsedate_to_datetime(pub)
            except Exception:
                article_date = None

        # Fall back to fetch time if no pub date
        if not article_date:
            fetched = item.get("fetched_at", "")
            if fetched:
                try:
                    article_date = datetime.fromisoformat(fetched.replace("Z", "+00:00"))
                except Exception:
                    continue
            else:
                continue

        # Make timezone-aware
        if article_date.tzinfo is None:
            article_date = article_date.replace(tzinfo=timezone.utc)

        if article_date > cutoff:
            item["_sort_date"] = article_date.isoformat()
            out.append(item)

    # Newest first
    out.sort(key=lambda x: x.get("_sort_date", ""), reverse=True)
    return out


def generate_memes(news_items, count):
    news_text = "\n".join(
        f"{i+1}. [{x['source']}] {x['title']}\n   {x['url']}"
        for i, x in enumerate(news_items[:10])
    )
    system_prompt = """You are a crypto comedian. Turn news headlines into funny meme ideas.

RULES:
- Each idea has: 1) CONCEPT (1-2 sentences), 2) CAPTION (under 100 chars), 3) IMAGE PROMPT (detailed, in English, for image generation).
- Use crypto-native slang: rug, wagmi, ngmi, gm, ser, anon, alpha, based, cope.
- Tone: irony, dark humor about hype.
- Do not promote scams or hate.
- Return STRICT JSON, no Markdown."""

    user_prompt = f"""FRESH NEWS (Base / crypto):

{news_text}

Generate {count} meme ideas. Return JSON:
{{"memes":[{{"news_index":1,"concept":"...","caption":"...","image_prompt":"...","tag":"..."}}]}}"""

    log("Requesting OpenCAP...")
    resp = ai.chat.completions.create(
        model="surplus/deepseek-v4-flash",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=1.0,
    )
    raw = resp.choices[0].message.content.strip()
    log(f"AI response ({len(raw)} chars): {raw[:150]}...")
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
        if raw.endswith("```"):
            raw = raw[:-3].strip()
    return json.loads(raw)["memes"]


def main():
    log("Loading config...")
    config = load_config()
    count = config.get("meme_count_per_run", 3)
    max_age = config.get("max_news_age_hours", 24)
    log(f"  count={count}, max_age={max_age}h")

    log("Loading news.json...")
    news = load_news()
    log(f"  Total in storage: {len(news)}")

    fresh = get_fresh_unused_news(news, max_age)
    log(f"Fresh unused news: {len(fresh)}")

    if not fresh:
        log("No fresh news — nothing to post")
        return

    log(f"Generating {count} memes...")
    memes = generate_memes(fresh, count)
    log(f"  Generated: {len(memes)}")

    used = set()
    for meme in memes:
        idx = meme.get("news_index", 1) - 1
        if idx < 0 or idx >= len(fresh):
            idx = 0
        item = fresh[idx]

        caption = (
            f"🎨 {meme.get('tag', 'base')}\n\n"
            f"💬 {meme['caption']}\n\n"
            f"💡 {meme['concept']}\n\n"
            f"🔗 {item['title']}\n{item['url']}"
        )

        try:
            tg_send_photo(meme["image_prompt"], caption)
            used.add(idx)
            log(f"  Meme #{meme.get('news_index')} posted")
        except Exception as e:
            log(f"  Failed to post: {e}")

    for idx in used:
        fresh[idx]["used"] = True
    save_news(news)
    log(f"Done. Used: {len(used)}")


try:
    main()
except Exception as e:
    log(f"CRITICAL ERROR: {e}")
    log(traceback.format_exc())
    sys.exit(1)

log("=" * 50)
