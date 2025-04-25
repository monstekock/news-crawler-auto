#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
news_crawler_automation.py
The-Sun · ScreenRant · US Weekly 최신 기사 5건씩 → Google Sheets
"""

import os, base64, html, time, requests, feedparser
from datetime import datetime
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials
from requests.adapters import HTTPAdapter, Retry

# ────────────────────────── 0. Google 인증 ──────────────────────────
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

# ────────────────────────── 1. RSS 피드 ────────────────────────────
FEEDS = {
    "The-Sun"    : "https://www.the-sun.com/entertainment/feed/",
    "ScreenRant" : "https://feeds.feedburner.com/screenrant/all",   # ← 프록시 URL
    "US Weekly"  : "https://www.usmagazine.com/feed/",
}

UA = {"User-Agent": "Mozilla/5.0"}

# requests 세션 (재시도)
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

# ────────────────────────── 2. 유틸 ────────────────────────────────
def clean(raw: str, maxlen=3000) -> str:
    return html.unescape(
        BeautifulSoup(raw, "html.parser").get_text(" ", strip=True)
    )[:maxlen]

def fmt(dt_struct) -> str:
    try:    return datetime(*dt_struct[:6]).strftime("%Y-%m-%d")
    except: return datetime.utcnow().strftime("%Y-%m-%d")

def save(rows):            # rows = list[list[str]]
    if rows:
        sheet.append_rows(rows, value_input_option="RAW")

# ────────────────────────── 3. RSS 수집 ────────────────────────────
def fetch_xml(url: str, tries=5, pause=2.0) -> str | None:
    for i in range(tries):
        try:
            r = sess.get(url, timeout=30)
            if r.ok: return r.text
        except requests.RequestException as e:
            if i == tries - 1:
                print(f"⚠ {url} 실패 → {e}")
        time.sleep(pause)
    return None

def collect(max_each=5):
    rows=[]
    for src, url in FEEDS.items():
        xml = fetch_xml(url)
        if not xml: continue
        feed = feedparser.parse(xml)
        print(f"{src}: {len(feed.entries)} entries")
        for e in feed.entries[:max_each]:
            rows.append([
                src,
                e.title,
                fmt(e.published_parsed) if hasattr(e,"published_parsed") else fmt(datetime.utcnow().timetuple()),
                e.link,
                clean(e.summary if hasattr(e,"summary") else ""),
            ])
    return rows

# ────────────────────────── 4. 실행 ────────────────────────────────
if __name__ == "__main__":
    data = collect()
    save(data)
    print(f"✓ saved {len(data)} articles (RSS)")
