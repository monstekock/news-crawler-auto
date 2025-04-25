#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
news_crawler_automation.py
TMZ · US Weekly · People RSS 최신 5건씩 Google Sheets 저장
"""

import os, base64, html, feedparser, requests
from datetime import datetime
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials

# ── 0. Google 인증 ───────────────────────────────
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

SHEET_ID   = "1IBkE0pECiWpF9kLdzEz7-1E-XyRBA02xiVHvwJCwKbc"
SHEET_NAME = "github news room"
sheet      = gc.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ── 1. RSS 피드 목록 ─────────────────────────────
FEEDS = {
    "TMZ":       "https://www.tmz.com/rss.xml",
    "US Weekly": "https://www.usmagazine.com/feed/",
    "People":    "https://people.com/feed/",
}

# ── 2. 유틸 ──────────────────────────────────────
def clean_html(raw: str, maxlen: int = 3000) -> str:
    txt = html.unescape(BeautifulSoup(raw, "html.parser").get_text(" ", strip=True))
    return txt[:maxlen]

def fmt(dt_struct) -> str:
    try:
        return datetime(*dt_struct[:6]).strftime("%Y-%m-%d")
    except Exception:
        return datetime.utcnow().strftime("%Y-%m-%d")

def save(rows):
    for r in rows:
        sheet.append_row(r, value_input_option="RAW")

# ── 3. 수집 ──────────────────────────────────────
def collect(max_each: int = 5):
    out = []
    for src, url in FEEDS.items():
        feed = feedparser.parse(url)
        for e in feed.entries[:max_each]:
            title = e.title
            link  = e.link
            date  = fmt(e.published_parsed) if hasattr(e, "published_parsed") else fmt(datetime.utcnow().timetuple())
            body  = clean_html(e.summary if hasattr(e, "summary") else "")
            out.append([src, title, date, link, body])
    return out

# ── 4. 실행 ──────────────────────────────────────
if __name__ == "__main__":
    rows = collect()
    save(rows)
    print(f"✓ saved {len(rows)} articles via RSS")
