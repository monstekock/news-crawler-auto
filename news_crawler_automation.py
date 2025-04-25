#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
news_crawler_automation.py
The-Sun · ScreenRant · US Weekly RSS 최신 5건씩 → Google Sheets
"""

import os, base64, html, time, feedparser, requests
from datetime import datetime
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials
from requests.adapters import HTTPAdapter, Retry

# ── 0. Google 인증 ──────────────────────────────────────────────
B64 = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_B64")
if not B64:
    raise RuntimeError("env GOOGLE_APPLICATION_CREDENTIALS_B64 not set")

with open("service_account.json", "wb") as f:
    f.write(base64.b64decode(B64))

creds = Credentials.from_service_account_file(
    "service_account.json",
    scopes=["https://www.googleapis.com/auth/spreadsheets"],
)
gc     = gspread.authorize(creds)
sheet  = gc.open_by_key("1IBkE0pECiWpF9kLdzEz7-1E-XyRBA02xiVHvwJCwKbc") \
            .worksheet("github news room")

# ── 1. RSS 목록 ────────────────────────────────────────────────
FEEDS = {
    "The-Sun"    : "https://www.the-sun.com/entertainment/feed/",
    "ScreenRant" : "https://screenrant.com/feed/",
    "US Weekly"  : "https://www.usmagazine.com/feed/",
}

UA = {"User-Agent": "Mozilla/5.0"}

# requests 세션 + 재시도 설정
sess = requests.Session()
sess.headers.update(UA)
sess.mount(
    "https://",
    HTTPAdapter(
        max_retries=Retry(
            total=3,
            backoff_factor=1.5,
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False,
        )
    ),
)

# ── 2. 유틸 ────────────────────────────────────────────────────
def clean(raw: str, maxlen=3000) -> str:
    return html.unescape(BeautifulSoup(raw, "html.parser").get_text(" ", strip=True))[:maxlen]

def fmt(dt_struct) -> str:
    try:    return datetime(*dt_struct[:6]).strftime("%Y-%m-%d")
    except: return datetime.utcnow().strftime("%Y-%m-%d")

def save(rows):
    if rows:
        sheet.append_rows(rows, value_input_option="RAW")

# ── 3. RSS 수집 ────────────────────────────────────────────────
def fetch_feed(url: str, tries: int = 3, pause: float = 2.0) -> str | None:
    """RSS XML 텍스트 반환 (실패 시 None)"""
    for i in range(tries):
        try:
            resp = sess.get(url, timeout=30)
            if resp.ok:
                return resp.text
        except requests.RequestException as e:
            if i == tries - 1:
                print(f"⚠ {url} 실패 → {e}")
            time.sleep(pause)
    return None  # 3회 모두 실패

def collect(max_each=5):
    out = []
    for src, url in FEEDS.items():
        xml = fetch_feed(url)
        if not xml:
            continue                     # 이 피드는 건너뛰고 다음으로
        feed = feedparser.parse(xml)
        print(f"{src}: {len(feed.entries)} entries")
        for e in feed.entries[:max_each]:
            out.append([
                src,
                e.title,
                fmt(e.published_parsed) if hasattr(e, "published_parsed") else fmt(datetime.utcnow().timetuple()),
                e.link,
                clean(e.summary if hasattr(e, "summary") else ""),
            ])
    return out

# ── 4. 실행 ───────────────────────────────────────────────────
if __name__ == "__main__":
    rows = collect()
    if rows:
        save(rows)
        print(f"✓ saved {len(rows)} articles (RSS)")
    else:
        print("⚠ 0 articles — 모든 RSS 요청이 실패했습니다.")
