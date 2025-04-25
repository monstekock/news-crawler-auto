import requests, os, base64, gspread
from bs4 import BeautifulSoup
from google.oauth2.service_account import Credentials
from datetime import datetime

# Google 인증 (파일 경로는 workflow에서 만들어 둠)
KEY_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file(KEY_FILE, scopes=SCOPES)
client = gspread.authorize(creds)

# 시트 설정
SHEET_ID   = '1IBkE0pECiWpF9kLdzEz7-1E-XyRBA02xiVHvwJCwKbc'
SHEET_NAME = 'github news room'          # ← 탭 이름
sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

def save(rows): 
    for r in rows: sheet.append_row(r, value_input_option='RAW')

def fmt(d): 
    try: return datetime.strptime(d,'%B %d, %Y').strftime('%Y-%m-%d')
    except: return datetime.now().strftime('%Y-%m-%d')

def crawl_tmz():
    base = 'https://www.tmz.com'
    soup = BeautifulSoup(requests.get(f'{base}/categories/breaking-news/').text,'html.parser')
    links = [base+a['href'] for a in soup.select('a.composition') if a['href'].startswith('/')]
    data=[]
    for url in links[:3]:
        s = BeautifulSoup(requests.get(url).text,'html.parser')
        title=s.select_one('h1.article-title'); body=s.select_one('div.article-content'); date=s.select_one('span.publish-date')
        if title and body:
            data.append(['TMZ', title.text.strip(), fmt(date.text if date else ''), url, body.text.strip()[:3000]])
    return data

def crawl_usweekly():
    base='https://www.usmagazine.com'
    soup=BeautifulSoup(requests.get(f'{base}/news/').text,'html.parser')
    links=[a['href'] for a in soup.select('a.content-card__link') if a['href'].startswith('https://')]
    data=[]
    for url in links[:3]:
        s=BeautifulSoup(requests.get(url).text,'html.parser')
        title=s.select_one('h1.post-title'); body=s.select_one('div.post-content'); date=s.select_one('time.published-date')
        if title and body:
            data.append(['US Weekly', title.text.strip(), fmt(date.text if date else ''), url, body.text.strip()[:3000]])
    return data

def crawl_people():
    base='https://people.com'
    soup=BeautifulSoup(requests.get(f'{base}/tag/the-scoop/').text,'html.parser')
    links=[base+a['href'] for a in soup.select('a[data-testid="CardLink"]') if a['href'].startswith('/')]
    data=[]
    for url in links[:3]:
        s=BeautifulSoup(requests.get(url).text,'html.parser')
        title=s.select_one('h1.headline'); body=s.select_one('div.article-body'); date=s.select_one('time.article-date')
        if title and body:
            data.append(['People', title.text.strip(), fmt(date.text if date else ''), url, body.text.strip()[:3000]])
    return data

if __name__ == '__main__':
    rows = crawl_tmz()+crawl_usweekly()+crawl_people()
    save(rows)
    print(f'{len(rows)} articles saved.')
