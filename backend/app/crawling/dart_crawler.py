import os
import requests
import json
from datetime import datetime, timedelta


def crawl_dart_reports(
    api_key: str,
    start_date: str,
    end_date: str,
    max_count: int = 1000,
    save_path: str = None,
):
    """
    DART 공시 원문 대량 수집 (최대 max_count건)
    - start_date, end_date: 'YYYYMMDD' 형식
    - save_path: 저장할 json 파일 경로
    """
    url = "https://opendart.fss.or.kr/api/list.json"
    params = {
        "crtfc_key": api_key,
        "bgn_de": start_date,
        "end_de": end_date,
        "page_count": 100,
        "page_no": 1,
    }
    all_reports = []
    while len(all_reports) < max_count:
        resp = requests.get(url, params=params)
        data = resp.json()
        if data.get("status") != "013" and data.get("list"):
            all_reports.extend(data["list"])
            if len(data["list"]) < 100:
                break
            params["page_no"] += 1
        else:
            break
    if save_path:
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(all_reports, f, ensure_ascii=False, indent=2)
    return all_reports


if __name__ == "__main__":
    api_key = os.getenv("DART_API_KEY") or "<YOUR_DART_API_KEY>"
    today = datetime.now().strftime("%Y%m%d")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
    save_path = "/app/data/crawled/dart_reports.json"
    crawl_dart_reports(api_key, week_ago, today, max_count=1000, save_path=save_path)
    print(f"Saved DART reports to {save_path}")
