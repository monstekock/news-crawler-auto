import os, base64, json, requests
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ────────────────────────────────────────────────────────────
# 0. GCP 키 (Base64 문자열 → 파일로 복원)
b64_key = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_B64")
if not b64_key:
    raise ValueError("❌ env GOOGLE_APPLICATION_CREDENTIALS_B64 가 없습니다.")

KEY_FILE = "service_account.json"
with open(KEY_FILE, "wb") as f:
    f.write(base64.b64decode(b64_key))

# ────────────────────────────────────────────────────────────
# 1. Google Sheets 인증
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file(KEY_FILE, scopes=SCOPES)
client = gspread.authorize(creds)

SHEET_ID   = "1IBkE0pECiWpF9kLdzEz7-1E-XyRBA02xiVHvwJCwKbc"
SHEET_NAME = "github news room"        # 시트 탭 이름 정확히
sheet      = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

# ────────────────────────────────────────────────────────────
def save_rows(rows: list[list[str]]):
    if rows:
        sheet.append_rows(rows, value_input_option="RAW")

def fmt(date_str: str) -> str:
    try:
        return datetime.strptime(date_str, "%B %d, %Y").strftime("%Y-%m-%d")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d")

# ── 2. 사이트별 크롤러 ─────────────────────────────────────
def crawl_tmz(max_n=3):
    base = "https://www.tmz.com"
    r = requests.get(f"{base}/categories/breaking-news/")
    soup = BeautifulSoup(r.text, "html.parser")
    links = [base + a["href"] for a in soup.select("a.composition") if a["href"].startswith("/")]
    rows = []
    for url in links[:max_n]:
        s = BeautifulSoup(requests.get(url).text, "html.parser")
        title = s.select_one("h1.article-title")
        body  = s.select_one("div.article-content")
        date  = s.select_one("span.publish-date")
        if title and body:
            rows.append([
                "TMZ", title.text.strip(), fmt(date.text.strip() if date else ""),
                url, body.text.strip().replace("\n", " ")[:3000]
            ])
    return rows

def crawl_usweekly(max_n=3):
    base = "https://www.usmagazine.com"
    r = requests.get(f"{base}/news/")
    soup = BeautifulSoup(r.text, "html.parser")
    links = [a["href"] for a in soup.select("a.content-card__link") if a["href"].startswith("https")]
    rows = []
    for url in links[:max_n]:
        s = BeautifulSoup(requests.get(url).text, "html.parser")
        title = s.select_one("h1.post-title")
        body  = s.select_one("div.post-content")
        date  = s.select_one("time.published-date")
        if title and body:
            rows.append([
                "US Weekly", title.text.strip(), fmt(date.text if date else ""),
                url, body.text.strip().replace("\n", " ")[:3000]
            ])
    return rows

def crawl_people(max_n=3):
    base = "https://people.com"
    r = requests.get(f"{base}/tag/the-scoop/")
    soup = BeautifulSoup(r.text, "html.parser")
    links = [base + a["href"] for a in soup.select('a[data-testid="CardLink"]') if a["href"].startswith("/")]
    rows = []
    for url in links[:max_n]:
        s = BeautifulSoup(requests.get(url).text, "html.parser")
        title = s.select_one("h1.headline")
        body  = s.select_one("div.article-body")
        date  = s.select_one("time.article-date")
        if title and body:
            rows.append([
                "People", title.text.strip(), fmt(date.text if date else ""),
                url, body.text.strip().replace("\n", " ")[:3000]
            ])
    return rows

# ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    data = crawl_tmz() + crawl_usweekly() + crawl_people()
    save_rows(data)
    print(f"{len(data)} articles saved.")
