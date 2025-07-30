import os
import json
import requests
import time
from tqdm import tqdm
from datetime import datetime, timedelta
import logging
from pathlib import Path

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# 기본 설정
BASE_URL = "https://opendart.fss.or.kr/api"
DATA_DIR = "/app/data/crawled/dart_api"
Path(DATA_DIR).mkdir(parents=True, exist_ok=True)

# API 요청 함수
def api_request(endpoint, params, sleep_time=1.0):
    """DART API 요청 공통 함수"""
    url = f"{BASE_URL}/{endpoint}"
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        time.sleep(sleep_time)  # API 서버 부하 방지
        return data
    except Exception as e:
        logger.error(f"API 요청 실패 ({endpoint}): {str(e)}")
        return {"status": "error", "message": str(e)}

# 1. 공시정보 수집 함수
def fetch_disclosure_list(api_key, start_date, end_date, corp_code=None, max_count=1000):
    """
    공시목록 API를 통해 공시 리스트 수집
    - start_date, end_date: 'YYYYMMDD' 형식
    """
    logger.info(f"공시목록 수집 중... {start_date}~{end_date} (corp_code: {corp_code})")

    params = {
        "crtfc_key": api_key,
        "bgn_de": start_date,
        "end_de": end_date,
        "page_count": 100,
        "page_no": 1,
    }

    # corp_code가 있는 경우 추가
    if corp_code:
        params["corp_code"] = corp_code


    if corp_code:
        params["corp_code"] = corp_code

    all_reports = []
    while len(all_reports) < max_count:
        data = api_request("list.json", params)

        if data.get("status") == "000":
            reports = data.get("list", [])
            all_reports.extend(reports)

            if len(reports) < 100:
                break

            params["page_no"] += 1
        else:
            logger.error(f"공시목록 API 응답 오류: {data}")
            break

    save_path = f"{DATA_DIR}/disclosure_list_{start_date}_{end_date}.json"
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(all_reports, f, ensure_ascii=False, indent=2)

    logger.info(f"공시목록 {len(all_reports)}건 수집 완료: {save_path}")
    return all_reports

# 2. 기업개황 정보 수집 함수
def fetch_company_info(api_key, corp_codes):
    """
    기업개황 정보 수집
    - corp_codes: 기업 고유번호 리스트
    """
    logger.info(f"기업개황 정보 수집 중... {len(corp_codes)}개 기업")

    results = {}
    for corp_code in tqdm(corp_codes):
        params = {
            "crtfc_key": api_key,
            "corp_code": corp_code,
        }

        data = api_request("company.json", params)
        results[corp_code] = data

    save_path = f"{DATA_DIR}/company_info.json"
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    logger.info(f"기업개황 정보 {len(results)}건 수집 완료: {save_path}")
    return results

# 3. 재무정보 수집 함수
def fetch_financial_data(api_key, corp_codes, bsns_year, reprt_code="11011"):
    """
    재무정보 수집
    - corp_codes: 기업 고유번호 리스트
    - bsns_year: 사업연도 (YYYY)
    - reprt_code: 보고서 코드 (11011:사업보고서, 11012:반기보고서, 11013:1분기, 11014:3분기)
    """
    logger.info(f"재무정보 수집 중... {len(corp_codes)}개 기업, {bsns_year}년")

    results = {"full": {}, "key": {}}
    for corp_code in tqdm(corp_codes):
        # 1. 전체 재무제표
        full_params = {
            "crtfc_key": api_key,
            "corp_code": corp_code,
            "bsns_year": bsns_year,
            "reprt_code": reprt_code,
            "fs_div": "CFS",  # 연결재무제표
        }

        full_data = api_request("fnlttSinglAcntAll.json", full_params, sleep_time=1.5)
        results["full"][corp_code] = full_data

        # 2. 주요계정 재무제표
        key_params = {
            "crtfc_key": api_key,
            "corp_code": corp_code,
            "bsns_year": bsns_year,
            "reprt_code": reprt_code,
            "fs_div": "CFS",  # 연결재무제표
        }

        key_data = api_request("fnlttSinglAcnt.json", key_params, sleep_time=1.5)
        results["key"][corp_code] = key_data

    save_path = f"{DATA_DIR}/financial_data_{bsns_year}_{reprt_code}.json"
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    logger.info(f"재무정보 {len(corp_codes)}개 기업 수집 완료: {save_path}")
    return results

# 4. 배당정보 수집 함수
def fetch_dividend_data(api_key, corp_codes, bsns_year):
    """
    배당정보 수집
    - corp_codes: 기업 고유번호 리스트
    - bsns_year: 사업연도 (YYYY)
    """
    logger.info(f"배당정보 수집 중... {len(corp_codes)}개 기업, {bsns_year}년")

    results = {}
    for corp_code in tqdm(corp_codes):
        params = {
            "crtfc_key": api_key,
            "corp_code": corp_code,
            "bsns_year": bsns_year,
        }

        data = api_request("alotMatter.json", params)
        results[corp_code] = data

    save_path = f"{DATA_DIR}/dividend_data_{bsns_year}.json"
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    logger.info(f"배당정보 {len(results)}건 수집 완료: {save_path}")
    return results

# 5. 최대주주 현황 수집 함수
def fetch_major_shareholders(api_key, corp_codes, bsns_year):
    """
    최대주주 현황 수집
    - corp_codes: 기업 고유번호 리스트
    - bsns_year: 사업연도 (YYYY)
    """
    logger.info(f"최대주주 현황 수집 중... {len(corp_codes)}개 기업, {bsns_year}년")

    results = {}
    for corp_code in tqdm(corp_codes):
        params = {
            "crtfc_key": api_key,
            "corp_code": corp_code,
            "bsns_year": bsns_year,
        }

        data = api_request("hyslr.json", params)
        results[corp_code] = data

    save_path = f"{DATA_DIR}/major_shareholders_{bsns_year}.json"
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    logger.info(f"최대주주 현황 {len(results)}건 수집 완료: {save_path}")
    return results

# 6. 임원 현황 수집 함수
def fetch_executives(api_key, corp_codes, bsns_year):
    """
    임원 현황 수집
    - corp_codes: 기업 고유번호 리스트
    - bsns_year: 사업연도 (YYYY)
    """
    logger.info(f"임원 현황 수집 중... {len(corp_codes)}개 기업, {bsns_year}년")

    results = {}
    for corp_code in tqdm(corp_codes):
        params = {
            "crtfc_key": api_key,
            "corp_code": corp_code,
            "bsns_year": bsns_year,
        }

        data = api_request("ofcr.json", params)
        results[corp_code] = data

    save_path = f"{DATA_DIR}/executives_{bsns_year}.json"
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    logger.info(f"임원 현황 {len(results)}건 수집 완료: {save_path}")
    return results

# 7. 고유번호 목록 가져오기
def fetch_corp_codes(api_key):
    """고유번호 목록 가져오기 (zip 파일로 제공)"""
    import zipfile
    import xml.etree.ElementTree as ET
    from io import BytesIO

    url = f"{BASE_URL}/corpCode.xml"
    params = {"crtfc_key": api_key}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()

        # ZIP 파일 열기
        with zipfile.ZipFile(BytesIO(response.content)) as z:
            with z.open('CORPCODE.xml') as f:
                root = ET.parse(f).getroot()

                corps = []
                for company in root.findall('list'):
                    corp_code = company.findtext('corp_code')
                    corp_name = company.findtext('corp_name')
                    stock_code = company.findtext('stock_code')

                    if stock_code and stock_code.strip():  # 상장기업만 수집
                        corps.append({
                            'corp_code': corp_code,
                            'corp_name': corp_name,
                            'stock_code': stock_code,
                        })

        save_path = f"{DATA_DIR}/corp_codes.json"
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(corps, f, ensure_ascii=False, indent=2)

        logger.info(f"고유번호 목록 {len(corps)}개 저장 완료: {save_path}")
        return corps

    except Exception as e:
        logger.error(f"고유번호 목록 요청 실패: {str(e)}")
        return []

# 전체 데이터 수집 파이프라인
def collect_all_data(api_key, years=None, top_n=100, reprt_codes=None):
    """
    전체 데이터 수집 파이프라인
    - years: 수집할 연도 목록 (기본값: 작년과 올해)
    - top_n: 시가총액 상위 몇 개 기업을 수집할지
    - reprt_codes: 수집할 보고서 코드 목록 (기본값: 사업보고서만)
    """
    # 기본 설정
    if years is None:
        current_year = datetime.now().year
        years = [str(current_year - 1), str(current_year)]

    if reprt_codes is None:
        reprt_codes = ["11011"]  # 사업보고서만

    # 1. 고유번호 목록 가져오기
    corps = fetch_corp_codes(api_key)
    corp_codes = [corp["corp_code"] for corp in corps[:top_n]]

    # 2. 공시목록 수집
    for year in years:
        start_date = f"{year}0101"
        end_date = f"{year}1231"
        fetch_disclosure_list(api_key, start_date, end_date)

    # 3. 기업개황 정보 수집
    fetch_company_info(api_key, corp_codes)

    # 4. 재무정보 수집
    for year in years:
        for reprt_code in reprt_codes:
            fetch_financial_data(api_key, corp_codes, year, reprt_code)

    # 5. 배당정보 수집
    for year in years:
        fetch_dividend_data(api_key, corp_codes, year)

    # 6. 최대주주 현황 수집
    for year in years:
        fetch_major_shareholders(api_key, corp_codes, year)

    # 7. 임원 현황 수집
    for year in years:
        fetch_executives(api_key, corp_codes, year)

    logger.info("모든 데이터 수집 완료")

# 메인 함수
if __name__ == "__main__":
    api_key = os.getenv("DART_API_KEY")
    if not api_key:
        logger.error("DART_API_KEY 환경변수가 설정되지 않았습니다.")
        exit(1)

    # 전체 데이터 수집 파이프라인 실행
    collect_all_data(
        api_key,
        years=["2024", "2023"],  # 2023년, 2024년 데이터
        top_n=100,  # 시가총액 상위 100개 기업
        reprt_codes=["11011"]  # 사업보고서만
    )
