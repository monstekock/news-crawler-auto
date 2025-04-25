# news_crawler_automation.py
# 크롤링 대상: TMZ, US Weekly, People.com
# 결과 저장: Google Sheets
# 실행 방식: GitHub Actions를 통해 매일 새벽 자동 실행

import requests
from bs4 import BeautifulSoup
import gspread
import google.auth
from datetime import datetime

# Google Sheets 인증: Application Default Credentials
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
creds, _ = google.auth.default(scopes=SCOPES)
client = gspread.authorize(creds)

# 공유된 Google Sheets 정보
SHEET_ID = '1IBkE0pECiWpF9kLdzEz7-1E-XyRBA02xiVHvwJCwKbc'
SHEET_NAME = 'Sheet1'
sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

def save_to_sheet(data):
    """크롤링한 데이터를 한 행씩 Google Sheets에 저장"""
    for item in data:
        sheet.append_row([
            item['source'],
            item['title'],
            item['date'],
            item['url'],
            item['body']
        ])

def format_date(date_str):
    """날짜 문자열을 YYYY-MM-DD 형식으로 변환"""
    try:
        return datetime.strptime(date_str, '%B %d, %Y').strftime('%Y-%m-%d')
    except:
        return datetime.now().strftime('%Y-%m-%d')

def crawl_tmz():
    """TMZ Breaking News 크롤러"""
    base = 'https://www.tmz.com'
    res = requests.get(f'{base}/categories/breaking-news/')
    soup = BeautifulSoup(res.text, 'html.parser')
    links = [
        base + a['href']
        for a in soup.select('a.composition')
        if a['href'].startswith('/')
    ]
    data = []
    for url in links[:3]:
        r = requests.get(url)
        s = BeautifulSoup(r.text, 'html.parser')
        title_el = s.select_one('h1.article-title')
        body_el = s.select_one('div.article-content')
        date_el = s.select_one('span.publish-date')
        if title_el and body_el:
            data.append({
                'source': 'TMZ',
                'title': title_el.get_text(strip=True),
                'date': format_date(date_el.get_text(strip=True) if date_el else ''),
                'url': url,
                'body': body_el.get_text(separator=' ', strip=True)[:3000]
            })
    return data

def crawl_usweekly():
    """US Weekly News 크롤러"""
    base = 'https://www.usmagazine.com'
    res = requests.get(f'{base}/news/')
    soup = BeautifulSoup(res.text, 'html.parser')
    links = [
        a['href']
        for a in soup.select('a.content-card__link')
        if a['href'].startswith('https://')
    ]
    data = []
    for url in links[:3]:
        r = requests.get(url)
        s = BeautifulSoup(r.text, 'html.parser')
        title_el = s.select_one('h1.post-title')
        body_el = s.select_one('div.post-content')
        date_el = s.select_one('time.published-date')
        if title_el and body_el:
            data.append({
                'source': 'US Weekly',
                'title': title_el.get_text(strip=True),
                'date': format_date(date_el.get_text(strip=True) if date_el else ''),
                'url': url,
                'body': body_el.get_text(separator=' ', strip=True)[:3000]
            })
    return data

def crawl_people():
    """People.com The Scoop 크롤러"""
    base = 'https://people.com'
    res = requests.get(f'{base}/tag/the-scoop/')
    soup = BeautifulSoup(res.text, 'html.parser')
    links = [
        base + a['href']
        for a in soup.select('a[data-testid="CardLink"]')
        if a['href'].startswith('/')
    ]
    data = []
    for url in links[:3]:
        r = requests.get(url)
        s = BeautifulSoup(r.text, 'html.parser')
        title_el = s.select_one('h1.headline')
        body_el = s.select_one('div.article-body')
        date_el = s.select_one('time.article-date')
        if title_el and body_el:
            data.append({
                'source': 'People',
                'title': title_el.get_text(strip=True),
                'date': format_date(date_el.get_text(strip=True) if date_el else ''),
                'url': url,
                'body': body_el.get_text(separator=' ', strip=True)[:3000]
            })
    return data

if __name__ == '__main__':
    all_data = crawl_tmz() + crawl_usweekly() + crawl_people()
    save_to_sheet(all_data)
    print(f"{len(all_data)} articles saved.")
