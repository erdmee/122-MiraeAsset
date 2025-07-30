import os
import json
import requests
from pathlib import Path
from tqdm import tqdm
from datetime import datetime
from typing import List, Dict, Any
import logging
from app.services.tools.elastic_vector_db import ElasticVectorDB

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

CURRENT_DATE = datetime.now().strftime("%Y%m%d")
logger.info(f"현재 날짜로 설정: {CURRENT_DATE}")

EMBEDDING_DIM = 1024  # CLOVA 임베딩 차원
DATA_DIR = "/app/data/crawled/dart_api"
es_disclosure = ElasticVectorDB(index_name="dart_disclosure")
es_financial = ElasticVectorDB(index_name="dart_financial")
es_company = ElasticVectorDB(index_name="dart_company")
es_events = ElasticVectorDB(index_name="dart_events")

# HyperCLOVA X 클라이언트 가져오기
try:
    from app.services.external.hyperclova_client import HyperClovaXClient

    HYPERCLOVA_AVAILABLE = True
    clova_client = HyperClovaXClient()
except ImportError:
    logger.warning(
        "HyperClovaXClient를 가져올 수 없습니다. 대체 클라이언트를 사용합니다."
    )
    HYPERCLOVA_AVAILABLE = False

# CLOVA 임베딩 API 설정
CLOVA_EMBEDDING_URL = (
    "https://clovastudio.stream.ntruss.com/testapp/v1/embeddings/HCX-003-embedding"
)
CLOVA_API_KEY = os.getenv("NAVER_CLOVA_API_KEY")
CLOVA_AVAILABLE = bool(CLOVA_API_KEY)


# 컬렉션 생성 함수는 불필요 (Elasticsearch는 인덱스 자동 생성)


# 2. CLOVA 임베딩 생성 함수
def create_embedding(text: str) -> List[float]:
    """CLOVA API로 텍스트 임베딩 생성"""
    if not CLOVA_AVAILABLE:
        logger.error("NAVER_CLOVA_API_KEY가 설정되지 않아 임베딩을 생성할 수 없습니다.")
        # 더미 임베딩 반환
        return [0.0] * EMBEDDING_DIM

    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {CLOVA_API_KEY}",
            "Accept": "application/json",
        }

        data = {"text": text, "normalize": True}

        response = requests.post(CLOVA_EMBEDDING_URL, headers=headers, json=data)

        if response.status_code == 200:
            result = response.json()
            embedding = result.get("result", {}).get("embedding", [])
            if embedding:
                return embedding
            else:
                logger.error(f"CLOVA 임베딩 응답에 임베딩 데이터가 없습니다: {result}")
                return [0.0] * EMBEDDING_DIM
        else:
            logger.error(
                f"CLOVA 임베딩 API 오류: {response.status_code}, {response.text}"
            )
            return [0.0] * EMBEDDING_DIM

    except Exception as e:
        logger.error(f"임베딩 생성 중 오류 발생: {str(e)}")
        return [0.0] * EMBEDDING_DIM


# 3. AI 분석 함수 (텍스트 분류, 요약 등)
def analyze_with_ai(prompt: str) -> Dict[str, Any]:
    """HyperCLOVA X를 사용한 텍스트 분석"""
    if not CLOVA_AVAILABLE:
        logger.error(
            "NAVER_CLOVA_API_KEY가 설정되지 않아 AI 분석을 수행할 수 없습니다."
        )
        return {
            "result": "AI 분석 불가능",
            "error": "NAVER_CLOVA_API_KEY가 설정되지 않았습니다.",
        }

    try:
        if HYPERCLOVA_AVAILABLE:
            # 내부 HyperClovaXClient 사용
            messages = [{"role": "user", "content": prompt}]
            response = clova_client.chat_completion(
                messages=messages, max_tokens=200, temperature=0.7
            )
            return {"result": response.get_content() if response else "응답 없음"}
        else:
            # 직접 API 호출
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {CLOVA_API_KEY}",
                "Accept": "application/json",
            }

            data = {
                "messages": [{"role": "user", "content": prompt}],
                "topP": 0.8,
                "maxTokens": 200,
                "temperature": 0.7,
                "repeatPenalty": 5.0,
                "includeAiFilters": True,
            }

            response = requests.post(
                "https://clovastudio.stream.ntruss.com/testapp/v1/chat-completions/HCX-003",
                headers=headers,
                json=data,
            )

            if response.status_code == 200:
                result = response.json()
                content = result.get("result", {}).get("message", {}).get("content", "")
                return {"result": content}
            else:
                logger.error(f"CLOVA API 오류: {response.status_code}, {response.text}")
                return {"result": "CLOVA API 오류 발생", "error": response.text}
    except Exception as e:
        logger.error(f"AI 분석 중 오류 발생: {str(e)}")
        return {"result": "오류 발생", "error": str(e)}


# 4. 공시정보 처리 및 임베딩 함수
def process_disclosure_data(file_path: str, batch_size: int = 100):
    """공시정보 처리 및 임베딩 (Elasticsearch)"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            disclosures = json.load(f)
        if not disclosures:
            logger.warning(f"처리할 공시 데이터가 없습니다: {file_path}")
            return
        logger.info(f"공시정보 {len(disclosures)}건 처리 시작")
        for i in range(0, len(disclosures), batch_size):
            batch = disclosures[i : i + batch_size]
            processed_data = []
            for disclosure in tqdm(
                batch, desc=f"공시 임베딩 처리 ({i}-{i+len(batch)}/{len(disclosures)})"
            ):
                content = f"{disclosure.get('corp_name', '')} {disclosure.get('report_nm', '')} - {disclosure.get('rm', '')}"
                impact_prompt = f"""
                다음 공시 내용의 주가에 대한 영향도를 분석해주세요:
                기업명: {disclosure.get('corp_name', '')}
                제목: {disclosure.get('report_nm', '')}
                내용: {disclosure.get('rm', '')}
                다음 중 하나로 분류해주세요: positive, negative, neutral
                분류 결과만 작성해주세요.
                """
                category_prompt = f"""
                다음 공시 제목을 다음 중 하나의 카테고리로 분류해주세요:
                제목: {disclosure.get('report_nm', '')}
                카테고리 목록: earnings, dividend, merger, investment, governance, capital, other
                분류 결과만 작성해주세요.
                """
                summary_prompt = f"""
                다음 공시 내용을 100자 내외로 요약해주세요:
                기업명: {disclosure.get('corp_name', '')}
                제목: {disclosure.get('report_nm', '')}
                내용: {disclosure.get('rm', '')}
                """
                impact_result = analyze_with_ai(impact_prompt)
                category_result = analyze_with_ai(category_prompt)
                summary_result = analyze_with_ai(summary_prompt)
                embedding = create_embedding(content)
                processed_data.append(
                    {
                        "corp_code": disclosure.get("corp_code", ""),
                        "corp_name": disclosure.get("corp_name", ""),
                        "stock_code": disclosure.get("stock_code", ""),
                        "rcept_no": disclosure.get("rcept_no", ""),
                        "report_nm": disclosure.get("report_nm", ""),
                        "rcept_dt": disclosure.get("rcept_dt", ""),
                        "flr_nm": disclosure.get("flr_nm", ""),
                        "rm": disclosure.get("rm", ""),
                        "content_summary": summary_result.get("result", ""),
                        "market_impact": impact_result.get("result", "neutral")
                        .lower()
                        .strip(),
                        "category": category_result.get("result", "other")
                        .lower()
                        .strip(),
                        "embedding": embedding,
                    }
                )
            es_disclosure.insert(processed_data)
            logger.info(f"공시정보 {len(batch)}건 Elasticsearch에 삽입 완료")
            proc_save_path = file_path.replace(
                ".json", f"_processed_{i}_{i+len(batch)}.json"
            )
            with open(proc_save_path, "w", encoding="utf-8") as f:
                json.dump(processed_data, f, ensure_ascii=False, indent=2)
        logger.info(f"공시정보 총 {len(disclosures)}건 처리 완료")
    except Exception as e:
        logger.error(f"공시정보 처리 중 오류 발생: {str(e)}")


# 5. 재무정보 처리 및 임베딩 함수
def process_financial_data(file_path: str, batch_size: int = 100):
    """재무정보 처리 및 임베딩 (Elasticsearch)"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        financials = []
        for corp_code, corp_data in data.get("full", {}).items():
            if corp_data.get("status") == "000":
                items = corp_data.get("list", [])
                corp_name = items[0].get("corp_name", "") if items else ""
                for item in items:
                    item["corp_code"] = corp_code
                    item["corp_name"] = corp_name
                    financials.append(item)
        if not financials:
            logger.warning(f"처리할 재무 데이터가 없습니다: {file_path}")
            return
        logger.info(f"재무정보 {len(financials)}건 처리 시작")
        for i in range(0, len(financials), batch_size):
            batch = financials[i : i + batch_size]
            processed_data = []
            for financial in tqdm(
                batch, desc=f"재무 임베딩 처리 ({i}-{i+len(batch)}/{len(financials)})"
            ):
                thstrm_amount = 0
                frmtrm_amount = 0
                growth_rate = 0.0
                try:
                    thstrm_amount = int(
                        financial.get("thstrm_amount", "0").replace(",", "") or "0"
                    )
                    frmtrm_amount = int(
                        financial.get("frmtrm_amount", "0").replace(",", "") or "0"
                    )
                    if frmtrm_amount != 0:
                        growth_rate = (
                            (thstrm_amount - frmtrm_amount) / abs(frmtrm_amount)
                        ) * 100
                except (ValueError, TypeError):
                    pass
                account_prompt = f"""
                다음 재무제표 계정에 대해 50자 내외로 간단히 설명해주세요:
                계정명: {financial.get('account_nm', '')}
                당기: {thstrm_amount:,}원
                전기: {frmtrm_amount:,}원
                성장률: {growth_rate:.2f}%
                """
                insight_prompt = f"""
                다음 재무 정보를 분석하여 투자 인사이트를 100자 내외로 제공해주세요:
                회사: {financial.get('corp_name', '')}
                계정: {financial.get('account_nm', '')}
                당기: {thstrm_amount:,}원
                전기: {frmtrm_amount:,}원
                성장률: {growth_rate:.2f}%
                """
                account_result = analyze_with_ai(account_prompt)
                insight_result = analyze_with_ai(insight_prompt)
                embedding_text = f"{financial.get('corp_name', '')} {financial.get('account_nm', '')} {account_result.get('result', '')} {insight_result.get('result', '')}"
                embedding = create_embedding(embedding_text)
                processed_data.append(
                    {
                        "corp_code": financial.get("corp_code", ""),
                        "corp_name": financial.get("corp_name", ""),
                        "bsns_year": financial.get("bsns_year", ""),
                        "reprt_code": financial.get("reprt_code", ""),
                        "fs_div": financial.get("fs_div", ""),
                        "sj_div": financial.get("sj_div", ""),
                        "account_nm": financial.get("account_nm", ""),
                        "thstrm_amount": thstrm_amount,
                        "frmtrm_amount": frmtrm_amount,
                        "growth_rate": growth_rate,
                        "account_summary": account_result.get("result", ""),
                        "analysis_insight": insight_result.get("result", ""),
                        "embedding": embedding,
                    }
                )
            es_financial.insert(processed_data)
            logger.info(f"재무정보 {len(batch)}건 Elasticsearch에 삽입 완료")
            proc_save_path = file_path.replace(
                ".json", f"_financial_processed_{i}_{i+len(batch)}.json"
            )
            with open(proc_save_path, "w", encoding="utf-8") as f:
                json.dump(processed_data, f, ensure_ascii=False, indent=2)
        logger.info(f"재무정보 총 {len(financials)}건 처리 완료")
    except Exception as e:
        logger.error(f"재무정보 처리 중 오류 발생: {str(e)}")


# 6. 배당정보 처리 및 임베딩 함수
def process_dividend_data(file_path: str, batch_size: int = 100):
    """배당정보 처리 및 임베딩 (Elasticsearch)"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        events = []
        for corp_code, corp_data in data.items():
            if corp_data.get("status") == "000":
                items = corp_data.get("list", [])
                corp_name = items[0].get("corp_name", "") if items else ""
                for item in items:
                    events.append(
                        {
                            "corp_code": corp_code,
                            "corp_name": corp_name,
                            "event_type": "dividend",
                            "event_dt": item.get("rpt_nm", "").replace(".", "")[:8],
                            "event_content": f"배당: {item.get('alot_rt', '')}%, 주당 {item.get('thstrm', '')}원",
                            "amount": int(
                                item.get("thstrm", "0").replace(",", "") or "0"
                            ),
                            "ratio": float(
                                item.get("alot_rt", "0").replace(",", "") or "0"
                            ),
                        }
                    )
        if not events:
            logger.warning(f"처리할 배당 데이터가 없습니다: {file_path}")
            return
        logger.info(f"배당정보 {len(events)}건 처리 시작")
        for i in range(0, len(events), batch_size):
            batch = events[i : i + batch_size]
            processed_data = []
            for event in tqdm(
                batch, desc=f"배당 임베딩 처리 ({i}-{i+len(batch)}/{len(events)})"
            ):
                impact_prompt = f"""
                다음 배당 정보의 주가 영향도를 분석해주세요:
                기업: {event.get('corp_name', '')}
                배당금: 주당 {event.get('amount', 0):,}원
                배당률: {event.get('ratio', 0):.2f}%
                영향도를 high, medium, low 중 하나로 분류해주세요.
                분류 결과만 작성해주세요.
                """
                impact_result = analyze_with_ai(impact_prompt)
                embedding_text = f"{event.get('corp_name', '')} 배당 {event.get('event_content', '')}"
                embedding = create_embedding(embedding_text)
                processed_data.append(
                    {
                        "corp_code": event.get("corp_code", ""),
                        "corp_name": event.get("corp_name", ""),
                        "event_type": event.get("event_type", ""),
                        "event_dt": event.get("event_dt", ""),
                        "event_content": event.get("event_content", ""),
                        "amount": event.get("amount", 0),
                        "ratio": event.get("ratio", 0.0),
                        "expected_impact": impact_result.get("result", "medium")
                        .lower()
                        .strip(),
                        "embedding": embedding,
                    }
                )
            es_events.insert(processed_data)
            logger.info(f"배당정보 {len(batch)}건 Elasticsearch에 삽입 완료")
            proc_save_path = file_path.replace(
                ".json", f"_events_processed_{i}_{i+len(batch)}.json"
            )
            with open(proc_save_path, "w", encoding="utf-8") as f:
                json.dump(processed_data, f, ensure_ascii=False, indent=2)
        logger.info(f"배당정보 총 {len(events)}건 처리 완료")
    except Exception as e:
        logger.error(f"배당정보 처리 중 오류 발생: {str(e)}")


# 7. 기업정보 처리 및 임베딩 함수
def process_company_info(file_path: str, batch_size: int = 100):
    """기업정보 처리 및 임베딩 (Elasticsearch)"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        companies = []
        for corp_code, corp_data in data.items():
            if corp_data.get("status") == "000":
                companies.append(
                    {
                        "corp_code": corp_code,
                        "corp_name": corp_data.get("corp_name", ""),
                        "stock_code": corp_data.get("stock_code", ""),
                        "corp_cls": corp_data.get("corp_cls", ""),
                        "est_dt": corp_data.get("est_dt", ""),
                        "acc_mt": corp_data.get("acc_mt", ""),
                        "ceo_nm": corp_data.get("ceo_nm", ""),
                        "induty_code": corp_data.get("induty_code", ""),
                    }
                )
        if not companies:
            logger.warning(f"처리할 기업 데이터가 없습니다: {file_path}")
            return
        logger.info(f"기업정보 {len(companies)}건 처리 시작")
        for i in range(0, len(companies), batch_size):
            batch = companies[i : i + batch_size]
            processed_data = []
            for company in tqdm(
                batch,
                desc=f"기업정보 임베딩 처리 ({i}-{i+len(batch)}/{len(companies)})",
            ):
                summary_prompt = f"""
                다음 기업에 대해 200자 내외로 사업 요약을 작성해주세요:
                기업명: {company.get('corp_name', '')}
                CEO: {company.get('ceo_nm', '')}
                설립일: {company.get('est_dt', '')}
                결산월: {company.get('acc_mt', '')}
                기업분류: {company.get('corp_cls', '')}
                """
                sector_prompt = f"""
                다음 기업의 섹터를 분류해주세요:
                기업명: {company.get('corp_name', '')}
                다음 섹터 중 하나로 분류해주세요:
                IT, 금융, 헬스케어, 에너지, 소비재, 산업재, 통신, 유틸리티, 부동산, 원자재, 기타
                분류 결과만 작성해주세요.
                """
                summary_result = analyze_with_ai(summary_prompt)
                sector_result = analyze_with_ai(sector_prompt)
                embedding_text = f"{company.get('corp_name', '')} {company.get('ceo_nm', '')} {summary_result.get('result', '')}"
                embedding = create_embedding(embedding_text)
                processed_data.append(
                    {
                        "corp_code": company.get("corp_code", ""),
                        "corp_name": company.get("corp_name", ""),
                        "stock_code": company.get("stock_code", ""),
                        "corp_cls": company.get("corp_cls", ""),
                        "est_dt": company.get("est_dt", ""),
                        "acc_mt": company.get("acc_mt", ""),
                        "ceo_nm": company.get("ceo_nm", ""),
                        "induty_code": company.get("induty_code", ""),
                        "business_summary": summary_result.get("result", ""),
                        "sector": sector_result.get("result", "기타").lower().strip(),
                        "embedding": embedding,
                    }
                )
            es_company.insert(processed_data)
            logger.info(f"기업정보 {len(batch)}건 Elasticsearch에 삽입 완료")
            proc_save_path = file_path.replace(
                ".json", f"_company_processed_{i}_{i+len(batch)}.json"
            )
            with open(proc_save_path, "w", encoding="utf-8") as f:
                json.dump(processed_data, f, ensure_ascii=False, indent=2)
        logger.info(f"기업정보 총 {len(companies)}건 처리 완료")
    except Exception as e:
        logger.error(f"기업정보 처리 중 오류 발생: {str(e)}")


# 8. 통합 실행 함수
def process_all_data(batch_size=50):
    """모든 데이터 처리 및 임베딩 실행 (Elasticsearch)"""
    # 1. 공시정보 처리
    disclosure_files = Path(DATA_DIR).glob("disclosure_list_*.json")
    for file_path in disclosure_files:
        logger.info(f"공시정보 파일 처리: {file_path}")
        process_disclosure_data(str(file_path), batch_size=batch_size)
    # 2. 재무정보 처리
    financial_files = Path(DATA_DIR).glob("financial_data_*.json")
    for file_path in financial_files:
        logger.info(f"재무정보 파일 처리: {file_path}")
        process_financial_data(str(file_path), batch_size=batch_size)
    # 3. 배당정보 처리
    dividend_files = Path(DATA_DIR).glob("dividend_data_*.json")
    for file_path in dividend_files:
        logger.info(f"배당정보 파일 처리: {file_path}")
        process_dividend_data(str(file_path), batch_size=batch_size)
    # 4. 기업정보 처리
    company_file = Path(DATA_DIR) / "company_info.json"
    if company_file.exists():
        logger.info("기업정보 파일 처리")
        process_company_info(str(company_file), batch_size=batch_size)
    logger.info("모든 데이터 처리 완료")


# 메인 함수
if __name__ == "__main__":
    api_key = os.getenv("NAVER_CLOVA_API_KEY")
    if not api_key:
        logger.error("NAVER_CLOVA_API_KEY 환경변수가 설정되지 않았습니다.")
        exit(1)
    logger.info(
        f"현재 날짜({CURRENT_DATE})를 기준으로 데이터 수집 및 처리를 진행합니다."
    )
    process_all_data(batch_size=50)
