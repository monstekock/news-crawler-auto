"""
news_crawler_automation.py
Google Sheets에 최신 연예 뉴스 3개씩 저장
(GitHub Actions self-hosted Runner에서 실행)

▶ 필요한 GitHub Secret
   GOOGLE_APPLICATION_CREDENTIALS_B64  ─ 서비스계정 JSON 을 base64 로 인코딩한 값
▶ Google Sheets
   스프레드시트 ID  : 1IBkE0pECiWpF9kLdzEz7-1E-XyRBA02xiVHvwJCwKbc
   워크시트(시트) 이름 : github news room
"""

import os, json, base64, io, requests
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ──────────────────────────────────────────────────────
# 1) Creds 불러오기 (Secret → service_account.json 임시 생성)
# ──────────────────────────────────────────────────────
B64 = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_B64")
if not B64:
    raise ValueError("❌ env GOOGLE_APPLICATION_CREDENTIALS_B64 가 없습니다.")

KEY_PATH = "service_account.json"
with open(KEY_PATH, "wb") as f:
    f.write(base64.b64decode(B64))

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file(KEY_PATH, scopes=SCOPES)
client = gspread.authorize(creds)

# ──────────────────────────────────────────────────────
# 2) Google Sheet 객체
# ──────────────────────────────────────────────────────
SHEET_ID   = "1IBkE0pECiWpF9kLdzEz7-1E-XyRBA02xiVHvwJCwKbc"
SHEET_NAME = "github news room"
sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

def save_rows(rows:list[dict]) -> None:
    """[{source,title,date,url,body}, …] → 시트 행 추가"""
    for r in rows:
        sheet.append_row([r["source"], r["title"], r["date"], r["url"], r["body"]])

# ──────────────────────────────────────────────────────
# 3) 도움 함수
# ──────────────────────────────────────────────────────
def fmt(date_str:str) -> str:
    try:
        return datetime.strptime(date_str, "%B %d, %Y").strftime("%Y-%m-%d")
    except:
        return datetime.utcnow().strftime("%Y-%m-%d")

HEADERS = {"User-Agent": "Mozilla/5.0"}   # 간단한 우회용

# ──────────────────────────────────────────────────────
# 4) 사이트별 크롤러
# ──────────────────────────────────────────────────────
def crawl_tmz() -> list[dict]:
    base = "https://www.tmz.com"
    res  = requests.get(f"{base}/categories/breaking-news/", headers=HEADERS, timeout=20)
    soup = BeautifulSoup(res.text, "html.parser")

    links = [base + a["href"] for a in soup.select('article a[data-analytics-id="CardLink"]')
             if a["href"].startswith("/")]
    print("TMZ links →", links)                          #  ← 디버그용

    data = []
    for url in links[:3]:
        s = BeautifulSoup(requests.get(url, headers=HEADERS, timeout=20).text, "html.parser")
        title = s.select_one("h1.article-title")
        body  = s.select_one("div.article-content")
        date  = s.select_one("span.publish-date")
        if title and body:
            data.append({
                "source":"TMZ",
                "title": title.text.strip(),
                "date" : fmt(date.text.strip() if date else ""),
                "url"  : url,
                "body" : body.text.strip().replace("\n"," ")[:3000]
            })
    return data

def crawl_usweekly() -> list[dict]:
    base = "https://www.usmagazine.com"
    soup = BeautifulSoup(requests.get(f"{base}/news/", headers=HEADERS, timeout=20).text, "html.parser")
    links = [a["href"] for a in soup.select("a.content-card__link") if a["href"].startswith("https://")]
    print("US Weekly links →", links)

    data=[]
    for url in links[:3]:
        s = BeautifulSoup(requests.get(url, headers=HEADERS, timeout=20).text, "html.parser")
        title = s.select_one("h1.post-title")
        body  = s.select_one("div.post-content")
        date  = s.select_one("time.published-date")
        if title and body:
            data.append({
                "source":"US Weekly",
                "title": title.text.strip(),
                "date" : fmt(date.text.strip() if date else ""),
                "url"  : url,
                "body" : body.text.strip().replace("\n"," ")[:3000]
            })
    return data

def crawl_people() -> list[dict]:
    base = "https://people.com"
    soup = BeautifulSoup(requests.get(f"{base}/tag/the-scoop/", headers=HEADERS, timeout=20).text, "html.parser")
    links = [base + a["href"] for a in soup.select('a[data-testid="CardLink"]') if a["href"].startswith("/")]
    print("People links →", links)

    data=[]
    for url in links[:3]:
        s = BeautifulSoup(requests.get(url, headers=HEADERS, timeout=20).text, "html.parser")
        title = s.select_one("h1.headline")
        body  = s.select_one("div.article-body")
        date  = s.select_one("time.article-date")
        if title and body:
            data.append({
                "source":"People",
                "title": title.text.strip(),
                "date" : fmt(date.text.strip() if date else ""),
                "url"  : url,
                "body" : body.text.strip().replace("\n"," ")[:3000]
            })
    return data

# ──────────────────────────────────────────────────────
# 5) 메인
# ──────────────────────────────────────────────────────
if __name__ == "__main__":
    rows = crawl_tmz() + crawl_usweekly() + crawl_people()
    print(f"✓ parsed {len(rows)} articles")
    if rows:
        save_rows(rows)
        print("✓ saved to sheet")
    else:
        print("⚠ 0 articles - selectors 또는 사이트 구조를 확인하세요.")
