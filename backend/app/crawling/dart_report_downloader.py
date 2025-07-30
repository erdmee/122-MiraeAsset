
import os
import json
import requests
import time
import random
from bs4 import BeautifulSoup
from tqdm import tqdm
from io import BytesIO
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer

def get_dart_html_url(rcept_no):
    return f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"

def get_dart_pdf_url(rcept_no):
    return f"https://dart.fss.or.kr/pdf/download/main.do?rcp_no={rcept_no}"

def fetch_pdf_and_extract_pages(pdf_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://dart.fss.or.kr/",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    try:
        resp = requests.get(pdf_url, timeout=20, headers=headers)
        resp.raise_for_status()
        pdf_bytes = BytesIO(resp.content)
        pages = []
        for i, page_layout in enumerate(extract_pages(pdf_bytes)):
            page_text = "".join(
                element.get_text() for element in page_layout if isinstance(element, LTTextContainer)
            ).strip()
            pages.append({"page": i+1, "text": page_text})
        return pages
    except Exception as e:
        return f"[ERROR] {e}"

def fetch_html_text(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://dart.fss.or.kr/",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    resp = requests.get(url, timeout=10, headers=headers)
    resp.encoding = resp.apparent_encoding
    soup = BeautifulSoup(resp.text, "html.parser")
    # 1. iframe id="iframe" 우선
    iframe = soup.find("iframe", id="iframe")
    if not iframe:
        # 2. id 없는 첫 번째 iframe도 시도
        iframes = soup.find_all("iframe")
        if iframes:
            iframe = iframes[0]
    if iframe and iframe.get("src"):
        iframe_url = "https://dart.fss.or.kr" + iframe.get("src")
        # sleep before iframe request
        time.sleep(random.uniform(0.5, 1.2))
        iframe_resp = requests.get(iframe_url, timeout=10, headers=headers)
        iframe_resp.encoding = iframe_resp.apparent_encoding
        iframe_soup = BeautifulSoup(iframe_resp.text, "html.parser")
        # 표(table)와 텍스트 모두 추출
        for tag in iframe_soup(["style", "script", "head", "title", "meta", "[document]"]):
            tag.decompose()
        # 표는 HTML로, 나머지는 텍스트로 추출
        tables = iframe_soup.find_all("table")
        table_html = "\n".join([str(t) for t in tables]) if tables else ""
        text = iframe_soup.get_text(separator="\n", strip=True)
        # 표+텍스트 합치기 (중복 제거)
        if table_html and text:
            return table_html + "\n" + text
        elif table_html:
            return table_html
        elif text:
            return text
    # 3. iframe이 없거나 실패하면 전체 HTML에서 텍스트 추출 (fallback)
    for tag in soup(["style", "script", "head", "title", "meta", "[document]"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    return text

def batch_download_and_extract(input_json, output_jsonl, limit=None):
    with open(input_json, encoding="utf-8") as f:
        reports = json.load(f)
    results = []
    for report in tqdm(reports[:limit] if limit else reports):
        rcept_no = report.get("rcept_no")
        corp_name = report.get("corp_name")
        report_nm = report.get("report_nm")
        pdf_url = get_dart_pdf_url(rcept_no)
        try:
            pages = fetch_pdf_and_extract_pages(pdf_url)
        except Exception as e:
            pages = f"[ERROR] {e}"
        results.append({
            "corp_name": corp_name,
            "report_nm": report_nm,
            "rcept_no": rcept_no,
            "pdf_url": pdf_url,
            "pages": pages
        })
        # sleep between each report to avoid server block
        time.sleep(random.uniform(1.5, 3.0))
    with open(output_jsonl, "w", encoding="utf-8") as f:
        for item in results:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"Saved {len(results)} extracted reports to {output_jsonl}")

if __name__ == "__main__":
    input_json = "/app/data/crawled/dart_reports.json"
    output_jsonl = "/app/data/crawled/dart_reports_extracted.jsonl"
    batch_download_and_extract(input_json, output_jsonl, limit=None)  # limit=None이면 전체
