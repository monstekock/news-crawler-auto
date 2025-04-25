import os, base64, json, requests
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ─── 1. 구글 키 복원 ─────────────────────────────────────────────
b64 = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_B64")
if not b64:
    raise ValueError("❌  env GOOGLE_APPLICATION_CREDENTIALS_B64 가 없습니다.")

KEY_FILE = "service_account.json"          # YAML 스텝에서 이미 생성
SCOPES    = ['https://www.googleapis.com/auth/spreadsheets']

creds  = Credentials.from_service_account_file(KEY_FILE, scopes=SCOPES)
client = gspread.authorize(creds)

# ─── 2. 시트 지정 ────────────────────────────────────────────────
SHEET_ID   = '1IBkE0pECiWpF9kLdzEz7-1E-XyRBA02xiVHvwJCwKbc'
SHEET_NAME = 'github news room'            # 정확히 동일하게

sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

def save_rows(rows):                       # rows: list[tuple]
    if rows:
        sheet.append_rows(rows)

# ─── 3. 크롤러들 ─────────────────────────────────────────────────
def fmt(d):                                # 날짜 정규화
    try:
        return datetime.strptime(d,'%B %d, %Y').strftime('%Y-%m-%d')
    except: return datetime.now().strftime('%Y-%m-%d')

def crawl_tmz():
    base='https://www.tmz.com'
    soup=BeautifulSoup(requests.get(f'{base}/categories/breaking-news/').text,'html.parser')
    links=[base+a['href'] for a in soup.select('a.composition') if a['href'].startswith('/')]
    out=[]
    for u in links[:3]:
        s=BeautifulSoup(requests.get(u).text,'html.parser')
        t=s.select_one('h1.article-title'); b=s.select_one('div.article-content'); d=s.select_one('span.publish-date')
        if t and b: out.append(('TMZ',t.text.strip(),fmt(d.text.strip() if d else ''),u,b.text.strip()[:3000]))
    return out

def crawl_people():
    base='https://people.com'
    soup=BeautifulSoup(requests.get(f'{base}/tag/the-scoop/').text,'html.parser')
    links=[base+a['href'] for a in soup.select('a[data-testid="CardLink"]') if a['href'].startswith('/')]
    out=[]
    for u in links[:3]:
        s=BeautifulSoup(requests.get(u).text,'html.parser')
        t=s.select_one('h1.headline'); b=s.select_one('div.article-body'); d=s.select_one('time.article-date')
        if t and b: out.append(('People',t.text.strip(),fmt(d.text.strip() if d else ''),u,b.text.strip()[:3000]))
    return out

# ─── 4. 실행 ────────────────────────────────────────────────────
if __name__ == "__main__":
    rows = crawl_tmz() + crawl_people()
    save_rows(rows)
    print(f"{len(rows)} articles saved.")
