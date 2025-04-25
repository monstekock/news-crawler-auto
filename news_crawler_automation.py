import requests
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os
import json
import base64

# Google Sheets 인증 (Base64로 인코딩된 서비스 계정 키를 환경변수에서 가져오기)
b64_key = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_B64")
if not b64_key:
    raise ValueError("GOOGLE_APPLICATION_CREDENTIALS_B64 is missing in environment variables.")

key_path = "service_account.json"
with open(key_path, "wb") as f:
    f.write(base64.b64decode(b64_key))

# 인증 및 클라이언트 생성
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file(key_path, scopes=SCOPES)
client = gspread.authorize(creds)

# Google Sheets 설정
SHEET_ID = '1IBkE0pECiWpF9kLdzEz7-1E-XyRBA02xiVHvwJCwKbc'
SHEET_NAME = 'github news room'
sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

# 공통 저장 함수
def save_to_sheet(data):
    for item in data:
        sheet.append_row([item['source'], item['title'], item['date'], item['url'], item['body']])

# 날짜 포맷
def format_date(date_str):
    try:
        return datetime.strptime(date_str, '%B %d, %Y').strftime('%Y-%m-%d')
    except:
        return datetime.now().strftime('%Y-%m-%d')

# TMZ 크롤러
def crawl_tmz():
    base = 'https://www.tmz.com'
    res = requests.get(f'{base}/categories/breaking-news/')
    soup = BeautifulSoup(res.text, 'html.parser')
    links = [base + a['href'] for a in soup.select('a.composition') if a['href'].startswith('/')]
    data = []
    for url in links[:3]:
        r = requests.get(url)
        s = BeautifulSoup(r.text, 'html.parser')
        title = s.select_one('h1.article-title')
        body = s.select_one('div.article-content')
        date = s.select_one('span.publish-date')
        if title and body:
            data.append({
                'source': 'TMZ',
                'title': title.text.strip(),
                'date': format_date(date.text.strip() if date else ''),
                'url': url,
                'body': body.text.strip().replace('\n', ' ')[:3000]
            })
    return data

# US Weekly 크롤러
def crawl_usweekly():
    base = 'https://www.usmagazine.com'
    res = requests.get(f'{base}/news/')
    soup = BeautifulSoup(res.text, 'html.parser')
    links = [a['href'] for a in soup.select('a.content-card__link') if a['href'].startswith('https://')]
    data = []
    for url in links[:3]:
        r = requests.get(url)
        s = BeautifulSoup(r.text, 'html.parser')
        title = s.select_one('h1.post-title')
        body = s.select_one('div.post-content')
        date = s.select_one('time.published-date')
        if title and body:
            data.append({
                'source': 'US Weekly',
                'title': title.text.strip(),
                'date': format_date(date.text.strip() if date else ''),
                'url': url,
                'body': body.text.strip().replace('\n', ' ')[:3000]
            })
    return data

# People 크롤러
def crawl_people():
    base = 'https://people.com'
    res = requests.get(f'{base}/tag/the-scoop/')
    soup = BeautifulSoup(res.text, 'html.parser')
    links = [base + a['href'] for a in soup.select('a[data-testid=\"CardLink\"]') if a['href'].startswith('/')]
    data = []
    for url in links[:3]:
        r = requests.get(url)
        s = BeautifulSoup(r.text, 'html.parser')
        title = s.select_one('h1.headline')
        body = s.select_one('div.article-body')
        date = s.select_one('time.article-date')
        if title and body:
            data.append({
                'source': 'People',
                'title': title.text.strip(),
                'date': format_date(date.text.strip() if date else ''),
                'url': url,
                'body': body.text.strip().replace('\n', ' ')[:3000]
            })
    return data

# 실행
if __name__ == '__main__':
    all_data = crawl_tmz() + crawl_usweekly() + crawl_people()
    save_to_sheet(all_data)
    print(f"{len(all_data)} articles saved.")
