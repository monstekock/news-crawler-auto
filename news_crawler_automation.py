#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
news_crawler_automation.py
The-Sun · ScreenRant · US Weekly RSS 최신 5건씩 Google Sheets에 저장
"""

import os, base64, html, requests, feedparser
from datetime import datetime
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials

# ───────────────────────────── 0. Google 인증 ─────────────────────────────
B64 = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_B64")
if not B64:
    raise RuntimeError("env GOOGLE_APPLICATION_CREDENTIALS_B64 not found")

with open("service_account.json", "wb") as f:
    f.write(base64.b64decode(B64))

creds = Credentials.from_service_account_file(
    "service_account.json",
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
gc = gspread.authorize(creds)
sheet = gc.open_by_key("1IBkE0pECiWpF9kLdzEz7-1E-XyRBA02xiVHvwJCwKbc") \
          .worksheet("github news room")

# ───────────────────────────── 1. RSS 피드 ────────────────────────────────
FEEDS = {
    "The-Sun"    : "https://www.the-sun.com/entertainment/feed/",
    "ScreenRant" : "https://screenrant.com/feed/",
    "US Weekly"  : "https://www.usmagazine.com/feed/",
}

HEADERS = {"User-Agent": "Mozilla/5.0"}   # 간단한 UA 우회

# ───────────────────────────── 2. 유틸 ────────────────────────────────────
def clean(raw: str, maxlen=3000) -> str:
    txt = html.unescape(BeautifulSoup(raw, "html.parser").get_text(" ", strip=True))
    return txt[:maxlen]

def fmt(dt_struct) -> str:
    try:    return datetime(*dt_struct[:6]).strftime("%Y-%m-%d")
    except: return datetime.utcnow().strftime("%Y-%m-%d")

def save(rows): sheet.append_rows(rows, value_input_option="RAW") if rows else None

# ───────────────────────────── 3. RSS 수집 ────────────────────────────────
def collect(max_each=5):
    out = []
    for src, url in FEEDS.items():
        xml   = requests.get(url, headers=HEADERS, timeout=20).text
        feed  = feedparser.parse(xml)
        print(f"{src}: {len(feed.entries)} entries parsed")
        for e in feed.entries[:max_each]:
            out.append([
                src,
                e.title,
                fmt(e.published_parsed) if hasattr(e,"published_parsed") else fmt(datetime.utcnow().timetuple()),
                e.link,
                clean(e.summary if hasattr(e,"summary") else "")
            ])
    return out

# ───────────────────────────── 4. 실행 ────────────────────────────────────
if __name__ == "__main__":
    rows = collect()
    save(rows)
    print(f"✓ saved {len(rows)} articles via RSS")
