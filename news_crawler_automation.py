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

# 추가 디버깅 출력 - JSON 값이 제대로 읽어지는지 확인
print("Google credentials:", google_credentials[:1000])  # 처음 1000글자만 출력 (값이 길기 때문에 일부만 확인)

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
        print(f"Saving item: {item}")  # 디버깅 출력 - 데이터를 저장하려는 항목 확인
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

# 실행
if __name__ == '__main__':
    all_data = crawl_tmz()
    save_to_sheet(all_data)
    print(f"{len(all_data)} articles saved.")
