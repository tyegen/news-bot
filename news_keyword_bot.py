"""
Telegram keyword news alert bot — GitHub Actions version.

Differences from the "keep a PC on" version:
- Runs ONCE per invocation instead of looping forever (GitHub Actions
  calls this on a schedule, e.g. every 10-15 minutes).
- Reads BOT_TOKEN and CHAT_ID from environment variables (GitHub
  Secrets), instead of hardcoding them in the file — this repo may end
  up public, so secrets must never be committed as plain text.
- Still deduplicates via seen_links.json, which the GitHub Actions
  workflow commits back to the repo after each run so state persists
  between runs.
"""

import json
import os
import urllib.parse

import feedparser
import requests

# ── CONFIG ────────────────────────────────────────────────────────────
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

KEYWORDS = [
    "Aytekin Kaya",
    "İncirliova",
    # add more terms here
]

EXTRA_FEEDS = [
    # "https://www.aydinsonhaber.com/rss",
]

SEEN_FILE = "seen_links.json"
MAX_SEEN_ENTRIES = 2000  # keep the file from growing forever
# ──────────────────────────────────────────────────────────────────────


def google_news_feed_url(keyword: str) -> str:
    q = urllib.parse.quote(keyword)
    return f"https://news.google.com/rss/search?q={q}&hl=tr&gl=TR&ceid=TR:tr"


def load_seen() -> set:
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_seen(seen: set) -> None:
    trimmed = list(seen)[-MAX_SEEN_ENTRIES:]
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(trimmed, f, ensure_ascii=False)


def turkish_lower(text: str) -> str:
    return text.replace("İ", "i").replace("I", "ı").lower()


def matches_keyword(text: str):
    text_l = turkish_lower(text)
    for kw in KEYWORDS:
        if turkish_lower(kw) in text_l:
            return kw
    return None


def send_telegram_message(text: str) -> None:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    resp = requests.post(
        url,
        data={"chat_id": CHAT_ID, "text": text, "disable_web_page_preview": False},
        timeout=15,
    )
    if not resp.ok:
        print(f"Telegram send failed: {resp.status_code} {resp.text}")


def build_feed_list() -> list:
    feeds = [google_news_feed_url(kw) for kw in KEYWORDS]
    feeds.extend(EXTRA_FEEDS)
    return feeds


def main():
    seen = load_seen()
    new_matches = 0

    for feed_url in build_feed_list():
        parsed = feedparser.parse(feed_url)
        for entry in parsed.entries:
            link = entry.get("link", "")
            title = entry.get("title", "")
            summary = entry.get("summary", "")

            if not link or link in seen:
                continue

            hit = matches_keyword(f"{title} {summary}")
            if hit:
                send_telegram_message(f'🔎 "{hit}" eşleşmesi:\n{title}\n{link}')
                new_matches += 1

            seen.add(link)

    save_seen(seen)
    print(f"Done. {new_matches} new match(es) sent.")


if __name__ == "__main__":
    main()
