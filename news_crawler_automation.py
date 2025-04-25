# news_crawler_automation.py
import os, base64, json, requests
from datetime import datetime
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials

# ---------- 1) GCP 서비스 계정 키 복원 ----------
b64_key = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_B64")
if not b64_key:
    raise ValueError("❌ env GOOGLE_APPLICATION_CREDENTIALS_B64 가 없습니다.")

KEY_FILE = "service_account.json"
with open(KEY_FILE, "wb") as f:
    f.write(base64.b64decode(b64_key))

# ---------- 2) Google Sheets 인증 ----------
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file(KEY_FILE, scopes=SCOPES)
client = gspread.authorize(creds)

SHEET_ID   = "1IBkE0pECiWpF9kLdzEz7-1E-XyRBA02xiVHvwJCwKbc"
SHEET_NAME = "github news room"          # 시트 탭 이름
sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

# ---------- 3) 공통 함수 ----------
def format_date(ds):
    try:
        return datetime.strptime(ds, "%B %d, %Y").strftime("%Y-%m-%d")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d")

def save(rows):
    for r in rows:
        sheet.append_row([r["src"], r["tit"], r["date"], r["url"], r["body"]])

# ---------- 4) 각 사이트 크롤러 ----------
def crawl_tmz():
    base = "https://www.tmz.com"
    soup = BeautifulSoup(requests.get(f"{base}/categories/breaking-news/").text, "html.parser")
    urls = [base+a["href"] for a in soup.select("a.composition")][:3]
    data = []
    for u in urls:
        s = BeautifulSoup(requests.get(u).text, "html.parser")
        data.append({
            "src":"TMZ",
            "tit": s.select_one("h1.article-title").text.strip(),
            "date": format_date(s.select_one("span.publish-date").text.strip()),
            "url": u,
            "body": (s.select_one("div.article-content").text.strip())[:3000]
        })
    return data

# ---------- 5) 실행 ----------
if __name__ == "__main__":
    rows = crawl_tmz()          # 필요 시 + crawl_usweekly() + crawl_people()
    save(rows)
    print(f"{len(rows)} articles saved.")
