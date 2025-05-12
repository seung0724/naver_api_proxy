import os
import time
import hmac
import base64
import hashlib
import requests
import json
import html
from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

# 광고 API 인증 정보
API_KEY = os.getenv("NAVER_API_KEY")
SECRET_KEY = os.getenv("NAVER_SECRET_KEY")
CUSTOMER_ID = os.getenv("NAVER_CUSTOMER_ID")

# 검색 OpenAPI 인증 정보
SEARCH_CLIENT_ID = os.getenv("NAVER_SEARCH_CLIENT_ID")
SEARCH_CLIENT_SECRET = os.getenv("NAVER_SEARCH_CLIENT_SECRET")

def generate_signature(timestamp, method, uri):
    message = f'{timestamp}.{method}.{uri}'
    signature = hmac.new(
        SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256
    ).digest()
    return base64.b64encode(signature).decode()

@app.route('/')
def home():
    return "✅ Naver Ads + BlogSearch Proxy is Running!"

# 🔍 네이버 블로그 검색 API
@app.route('/blogsearch')
def blogsearch():
    query = request.args.get('query')
    display = request.args.get('display', 10)
    start = request.args.get('start', 1)
    sort = request.args.get('sort', 'sim')

    headers = {
        'X-Naver-Client-Id': SEARCH_CLIENT_ID,
        'X-Naver-Client-Secret': SEARCH_CLIENT_SECRET
    }

    try:
        res = requests.get("https://openapi.naver.com/v1/search/blog", headers=headers, params={
            'query': query,
            'display': display,
            'start': start,
            'sort': sort
        })

        data = json.loads(res.text)

        for item in data.get("items", []):
            item["title"] = html.unescape(item["title"])
            item["description"] = html.unescape(item["description"])
            item["bloggername"] = html.unescape(item["bloggername"])

        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 📈 키워드 추천 (검색광고 API)
@app.route('/keywordstool')
def keywordstool():
    hint_keywords = request.args.get('hintKeywords')
    site_id = request.args.get('siteId', '')
    event = request.args.get('event', '')

    uri = '/keywordstool'
    url = f'https://api.naver.com{uri}'
    timestamp = str(int(time.time() * 1000))
    signature = generate_signature(timestamp, 'GET', uri)

    headers = {
        'X-Timestamp': timestamp,
        'X-API-KEY': API_KEY,
        'X-CUSTOMER': CUSTOMER_ID,
        'X-Signature': signature
    }

    try:
        res = requests.get(url, headers=headers, params={
            'hintKeywords': hint_keywords,
            'siteId': site_id,
            'event': event
        })
        return jsonify(res.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 📄 블로그 본문 추출기
@app.route('/blogbody')
def blogbody():
    blog_url = request.args.get('url')
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        res = requests.get(blog_url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')

        iframe = soup.find('iframe')
        if iframe and 'src' in iframe.attrs:
            iframe_url = 'https://blog.naver.com' + iframe['src']
            iframe_res = requests.get(iframe_url, headers=headers)
            iframe_soup = BeautifulSoup(iframe_res.text, 'html.parser')
            content = iframe_soup.find('div', class_='se-main-container')
            text = content.get_text(strip=True) if content else "본문 추출 실패"
        else:
            text = "iframe 없음 - 본문 추출 실패"

        return jsonify({"text": text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ✅ Render용: 0.0.0.0 + 환경변수 포트 바인딩
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
