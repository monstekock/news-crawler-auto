#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
news_crawler_automation.py
▶ TMZ · US Weekly · People 기사 본문을 Google Sheets 로 저장
▶ GitHub Actions / self-hosted runner용
"""

import os, json, base64, requests
from datetime import datetime
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials

# ──────────────────────────── ① 구글 인증 ────────────────────────────
B64_KEY = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_B64")   # ← 시크릿 이름 그대로
if not B64_KEY:
    raise ValueError("❌ env GOOGLE_APPLICATION_CREDENTIALS_B64 가 없습니다.")

KEY_PATH = "service_account.json"
with open(KEY_PATH, "wb") as f:
    f.write(base64.b64decode(B64_KEY))

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file(KEY_PATH, scopes=SCOPES)
client = gspread.authorize(creds)

# ──────────────────────────── ② 시트 설정 ────────────────────────────
SHEET_ID   = "1IBkE0pECiWpF9kLdzEz7-1E-XyRBA02xiVHvwJCwKbc"
SHEET_NAME = "github news room"
sheet      = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

def save_to_sheet(rows:list[dict]) -> None:
    """{source,title,date,url,body} dict → 시트 append"""
    for r in rows:
        sheet.append_row([r["source"], r["title"], r["date"], r["url"], r["body"]])

def fmt(date_str:str) -> str:
    try:
        return datetime.strptime(date_str, "%B %d, %Y").strftime("%Y-%m-%d")
    except Exception:
        return datetime.utcnow().strftime("%Y-%m-%d")

# ──────────────────────────── ③ 크롤러들 ────────────────────────────
def crawl_tmz(max_cnt:int=5) -> list[dict]:
    """TMZ ‘Breaking News’ 최신 기사 n 건"""
    base = "https://www.tmz.com"
    res  = requests.get(f"{base}/categories/breaking-news/")
    soup = BeautifulSoup(res.text, "html.parser")

    # 🔧 (수정) 2025-04 기준 카드 구조: <article> … <a data-analytics-id="CardLink" …>
    links = [
        (base + a["href"]) for a in soup.select('article a[data-analytics-id="CardLink"]')
        if a.get("href", "").startswith("/")
    ][:max_cnt]

    rows=[]
    for url in links:
        s  = BeautifulSoup(requests.get(url).text, "html.parser")
        title = s.select_one("h1.article__headline") or s.select_one("h1")
        body  = s.select_one("div.article__body")    or s.select_one("div.article-content")
        date  = s.select_one("time") or s.select_one("span.publish-date")
        if title and body:
            rows.append({
                "source": "TMZ",
                "title" : title.text.strip(),
                "date"  : fmt(date.text.strip() if date else ""),
                "url"   : url,
                "body"  : body.text.strip().replace("\n", " ")[:3000],
            })
    return rows

def crawl_usweekly(max_cnt:int=3) -> list[dict]:
    base = "https://www.usmagazine.com"
    soup = BeautifulSoup(requests.get(f"{base}/news/").text, "html.parser")
    links = [a["href"] for a in soup.select("a.content-card__link") if a["href"].startswith("https://")][:max_cnt]
    rows=[]
    for url in links:
        s=BeautifulSoup(requests.get(url).text,"html.parser")
        title=s.select_one("h1.post-title")
        body =s.select_one("div.post-content")
        date =s.select_one("time.published-date")
        if title and body:
            rows.append({
                "source":"US Weekly","title":title.text.strip(),
                "date":fmt(date.text.strip() if date else ""),
                "url":url,"body":body.text.strip().replace("\n"," ")[:3000]
            })
    return rows

def crawl_people(max_cnt:int=3) -> list[dict]:
    base="https://people.com"
    soup=BeautifulSoup(requests.get(f"{base}/tag/the-scoop/").text,"html.parser")
    links=[base+a["href"] for a in soup.select('a[data-testid="CardLink"]') if a["href"].startswith("/")][:max_cnt]
    rows=[]
    for url in links:
        s=BeautifulSoup(requests.get(url).text,"html.parser")
        title=s.select_one("h1.headline")
        body =s.select_one("div.article-body")
        date =s.select_one("time.article-date")
        if title and body:
            rows.append({
                "source":"People","title":title.text.strip(),
                "date":fmt(date.text.strip() if date else ""),
                "url":url,"body":body.text.strip().replace("\n"," ")[:3000]
            })
    return rows

# ──────────────────────────── ④ 실행 ────────────────────────────
if __name__ == "__main__":
    data = crawl_tmz() + crawl_usweekly() + crawl_people()
    save_to_sheet(data)
    print(f"{len(data)} articles saved.")
