import os
import json
from google.oauth2 import service_account
import gspread
from datetime import datetime

# Google Sheets 인증
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# GitHub Secrets에서 service_account.json의 내용을 가져오기
google_credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# 디버깅 출력 - 환경 변수 확인
if google_credentials is None or google_credentials == "":
    print("Environment variable 'GOOGLE_APPLICATION_CREDENTIALS' is not set correctly.")
else:
    print("Successfully retrieved environment variable.")

# Google 인증 처리
if google_credentials:
    try:
        key_json = json.loads(google_credentials)
        creds = service_account.Credentials.from_service_account_info(key_json)
        client = gspread.authorize(creds)
    except json.JSONDecodeError as e:
        print("Failed to decode JSON from environment variable:", e)
        exit(1)
else:
    print("Unable to retrieve valid credentials from the environment.")
    exit(1)

# 공유된 Google Sheets ID
SHEET_ID = '1IBkE0pECiWpF9kLdzEz7-1E-XyRBA02xiVHvwJCwKbc'
SHEET_NAME = 'Sheet1'
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
    links = [base + a['href'] for a in soup.select('a.composition') if a['href'].startswith('/')]  # 기사 링크들
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
    links = [base + a['href'] for a in soup.select('a[data-testid="CardLink"]') if a['href'].startswith('/')] 
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
