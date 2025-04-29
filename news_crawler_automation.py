#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
news_crawler_automation.py
The-Sun · US Weekly (본문 content만, 300자 이상만 저장)
"""

import os, base64, html, time, requests, feedparser
from datetime import datetime
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials
from requests.adapters import HTTPAdapter, Retry

# ─────────────────────── 0. Google 인증 ───────────────────────
B64 = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_B64")
if not B64:
    raise RuntimeError("env GOOGLE_APPLICATION_CREDENTIALS_B64 not set")

with open("service_account.json", "wb") as f:
    f.write(base64.b64decode(B64))

creds = Credentials.from_service_account_file(
    "service_account.json",
    scopes=["https://www.googleapis.com/auth/spreadsheets"],
)
gc    = gspread.authorize(creds)
sheet = gc.open_by_key("1IBkE0pECiWpF9kLdzEz7-1E-XyRBA02xiVHvwJCwKbc") \
           .worksheet("github news room")

# ─────────────────────── 1. RSS 목록 ─────────────────────────
FEEDS = {
    "The-Sun":         "https://www.the-sun.com/entertainment/feed/",
    "US Weekly":       "https://www.usmagazine.com/feed/",
    "MMA Fighting":    "https://www.mmafighting.com/rss/current",
    "Bloody Elbow":    "https://www.bloodyelbow.com/rss/current",
}

UA = {"User-Agent": "Mozilla/5.0"}

sess = requests.Session()
sess.headers.update(UA)
sess.mount(
    "https://",
    HTTPAdapter(
        max_retries=Retry(
            total=5,
            backoff_factor=2.0,
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False,
        )
    ),
)

# ─────────────────────── 2. 유틸 ─────────────────────────────
def clean(raw: str, maxlen=3000) -> str:
    return html.unescape(
        BeautifulSoup(raw, "html.parser").get_text(" ", strip=True)
    )[:maxlen]

fmt = lambda t: datetime(*t[:6]).strftime("%Y-%m-%d")

def extract_content(entry, min_len=100):
    if hasattr(entry, "content") and entry.content:
        raw = entry.content[0].value
        text = clean(raw)
        return text if len(text) >= min_len else None
    return None

def save(rows):                                   # rows=list[list[str]]
    if rows:
        sheet.append_rows(rows, value_input_option="RAW")

# ─────────────────────── 3. RSS 수집 ─────────────────────────
def fetch_xml(url: str, tries=5, pause=2.0):
    for i in range(tries):
        try:
            r = sess.get(url, timeout=30)
            if r.ok:
                return r.text
        except requests.RequestException as e:
            if i == tries - 1:
                print(f"⚠ {url} 실패 → {e}")
        time.sleep(pause)
    return None

def collect(max_each=10):
    rows = []
    for src, url in FEEDS.items():
        xml = fetch_xml(url)
        if not xml:
            continue
        feed = feedparser.parse(xml)
        print(f"{src}: {len(feed.entries)} entries")
        for e in feed.entries[:max_each]:
            body = extract_content(e)
            if body:
                rows.append([
                    src,
                    e.title,
                    fmt(e.published_parsed) if hasattr(e, "published_parsed") else fmt(datetime.utcnow().timetuple()),
                    e.link,
                    body,
                ])
    return rows

# ─────────────────────── 4. 실행 ────────────────────────────
if __name__ == "__main__":
    data = collect()
    save(data)
    print(f"✓ saved {len(data)} articles (RSS)")
