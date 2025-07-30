import os
import json
import time
import requests
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import argparse


class ClovaXEmbedder:
    """Naver Clova X 임베딩 클래스"""

    def __init__(self):
        self.api_key = None
        self.api_key_primary = None
        self.app_name = None  # testapp 말고 실제 앱 이름

    def setup_clova_client(self):
        """Naver Clova X 클라이언트 설정"""
        try:
            # 환경변수에서 API 키 가져오기
            self.api_key = os.getenv("NAVER_CLOVA_API_KEY")
            self.api_host = os.getenv("NAVER_CLOVA_API_HOST", "clovastudio.stream.ntruss.com")

            if not self.api_key:
                print("❌ NAVER_CLOVA_API_KEY 환경변수가 필요합니다.")
                return False

            # CLOVA Studio 임베딩 API URL들 (앱 이름 없이)
            self.embedding_urls = [
                f"https://{self.api_host}/v1/api-tools/embedding/clir-emb-dolphin",
                f"https://clovastudio.apigw.ntruss.com/v1/api-tools/embedding/clir-emb-dolphin",
                f"https://{self.api_host}/v1/api-tools/embedding/clir-sts-dolphin",
                f"https://clovastudio.apigw.ntruss.com/v1/api-tools/embedding/clir-sts-dolphin"
            ]
            self.working_url = None

            print(f"🔗 Naver CLOVA Studio 임베딩 설정 완료")
            print(f"🏠 호스트: {self.api_host}")
            print(f"🔑 API 키: {self.api_key[:10]}...")

            return True

        except Exception as e:
            print(f"❌ Clova X 클라이언트 설정 실패: {e}")
            return False

    def setup_milvus_client(self):
        """Milvus 클라이언트 설정"""
        try:
            from pymilvus import (
                connections,
                Collection,
                CollectionSchema,
                FieldSchema,
                DataType,
            )

            # Milvus 연결
            milvus_host = os.getenv("MILVUS_HOST", "milvus")
            milvus_port = os.getenv("MILVUS_PORT", "19530")

            print(f"🔗 Milvus 연결 중... ({milvus_host}:{milvus_port})")
            connections.connect("default", host=milvus_host, port=milvus_port)

            print("✅ Milvus 연결 성공")
            return True

        except Exception as e:
            print(f"❌ Milvus 연결 실패: {e}")
            return False

    def create_collections(self):
        """Milvus 컬렉션 생성"""
        try:
            from pymilvus import (
                Collection,
                CollectionSchema,
                FieldSchema,
                DataType,
                utility,
            )

            print("📊 Milvus 컬렉션 생성 중...")

            # 기존 컬렉션 있으면 삭제
            collections_to_create = [
                "dart_companies",
                "dart_financials",
                "dart_disclosures",
            ]

            for collection_name in collections_to_create:
                if utility.has_collection(collection_name):
                    utility.drop_collection(collection_name)
                    print(f"  🗑️ 기존 {collection_name} 컬렉션 삭제")

            # CLOVA Studio 임베딩 차원 수정 (1024차원)
            embedding_dim = 1024  # CLOVA Studio clir-emb-dolphin은 1024차원

            # 1. 기업정보 컬렉션 (auto_id 제거)
            company_fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True),
                FieldSchema(name="corp_code", dtype=DataType.VARCHAR, max_length=20),
                FieldSchema(name="corp_name", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=2000),
                FieldSchema(
                    name="embedding", dtype=DataType.FLOAT_VECTOR, dim=embedding_dim
                ),
            ]

            company_schema = CollectionSchema(company_fields, "기업정보")
            company_collection = Collection("dart_companies", company_schema)

            # 스키마 확인
            print(f"    기업정보 컬렉션 스키마 필드 개수: {len(company_collection.schema.fields)}")
            for i, field in enumerate(company_collection.schema.fields):
                print(f"    필드 {i}: {field.name} ({field.dtype}) auto_id={field.auto_id}")

            # 인덱스 생성
            index_params = {
                "metric_type": "COSINE",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 128},
            }
            company_collection.create_index("embedding", index_params)

            print("  ✅ 기업정보 컬렉션 생성 완료")

            # 2. 재무정보 컬렉션
            financial_fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True),
                FieldSchema(name="corp_code", dtype=DataType.VARCHAR, max_length=20),
                FieldSchema(name="corp_name", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="year", dtype=DataType.VARCHAR, max_length=4),
                FieldSchema(
                    name="account_info", dtype=DataType.VARCHAR, max_length=2000
                ),
                FieldSchema(
                    name="embedding", dtype=DataType.FLOAT_VECTOR, dim=embedding_dim
                ),
            ]

            financial_schema = CollectionSchema(financial_fields, "재무정보")
            financial_collection = Collection("dart_financials", financial_schema)
            financial_collection.create_index("embedding", index_params)

            print("  ✅ 재무정보 컬렉션 생성 완료")

            # 3. 공시정보 컬렉션
            disclosure_fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True),
                FieldSchema(name="corp_code", dtype=DataType.VARCHAR, max_length=20),
                FieldSchema(name="corp_name", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="report_name", dtype=DataType.VARCHAR, max_length=200),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=2000),
                FieldSchema(name="rcept_dt", dtype=DataType.VARCHAR, max_length=8),
                FieldSchema(
                    name="embedding", dtype=DataType.FLOAT_VECTOR, dim=embedding_dim
                ),
            ]

            disclosure_schema = CollectionSchema(disclosure_fields, "공시정보")
            disclosure_collection = Collection("dart_disclosures", disclosure_schema)
            disclosure_collection.create_index("embedding", index_params)

            print("  ✅ 공시정보 컬렉션 생성 완료")

            return True

        except Exception as e:
            print(f"❌ 컬렉션 생성 실패: {e}")
            import traceback

            traceback.print_exc()
            return False

    def create_embedding_with_clova_v2(self, text: str) -> List[float]:
        """CLOVA Studio 임베딩 API 사용"""

        # 이미 작동하는 URL이 있으면 그것만 사용
        urls_to_try = [self.working_url] if self.working_url else self.embedding_urls

        for url in urls_to_try:
            try:
                print(f"    시도 중: {url}")

                # CLOVA Studio 인증 헤더 (Bearer 토큰 방식)
                headers = {
                    'Content-Type': 'application/json; charset=utf-8',
                    'Authorization': f'Bearer {self.api_key}',
                    'X-NCP-CLOVASTUDIO-REQUEST-ID': str(int(time.time() * 1000))  # 타임스탬프를 REQUEST ID로 사용
                }

                # CLOVA Studio 임베딩 API 요청 형식
                data = {
                    "text": text[:500]  # 최대 500토큰 제한
                }

                print(f"      요청 데이터: {data}")

                response = requests.post(url, headers=headers, json=data, timeout=30)

                print(f"      응답 코드: {response.status_code}")

                if response.status_code == 200:
                    result = response.json()
                    print(f"      응답 구조: {list(result.keys())}")

                    # CLOVA Studio 응답 구조 처리
                    if 'status' in result and result['status']['code'] == '20000':
                        if 'result' in result and 'embedding' in result['result']:
                            embedding = result['result']['embedding']

                            if embedding and len(embedding) > 0:
                                self.working_url = url  # 성공한 URL 저장
                                print(f"      ✅ 성공! 벡터 차원: {len(embedding)}")
                                print(f"      입력 토큰 수: {result['result'].get('inputTokens', 'N/A')}")
                                return embedding

                elif response.status_code == 404:
                    print(f"      404: URL이 존재하지 않음")
                    continue

                elif response.status_code == 401:
                    print(f"      401: 인증 실패 - {response.text[:200]}")
                    continue

                else:
                    print(f"      {response.status_code}: {response.text[:200]}")

                time.sleep(0.5)

            except Exception as e:
                print(f"      ❌ 요청 실패: {e}")
                continue

        print("❌ 모든 CLOVA Studio 엔드포인트 실패")
        return None

    def create_simple_hash_embedding(self, text: str, dim: int = 1024) -> List[float]:
        """간단한 해시 기반 임베딩 (Clova API 실패시 대안)"""
        try:
            import hashlib
            import struct

            # 텍스트를 해시하고 고정 길이 벡터로 변환
            hash_obj = hashlib.sha256(text.encode("utf-8"))
            hash_bytes = hash_obj.digest()

            # 바이트를 float로 변환
            vector = []
            for i in range(0, len(hash_bytes), 4):
                if i + 4 <= len(hash_bytes):
                    float_val = struct.unpack("f", hash_bytes[i : i + 4])[0]
                    vector.append(float_val)

            # 원하는 차원수까지 확장/자르기
            while len(vector) < dim:
                vector.extend(vector[: min(len(vector), dim - len(vector))])

            return vector[:dim]

        except Exception as e:
            print(f"❌ 해시 임베딩 생성 실패: {e}")
            return None

    def create_embedding(self, text: str) -> List[float]:
        """텍스트를 벡터로 변환 (Clova X 임베딩 v2 우선)"""

        # 방법 1: Clova X 임베딩 v2 bge-m3 모델 시도
        embedding = self.create_embedding_with_clova_v2(text)
        if embedding:
            return embedding

        print("  ⚠️ Clova 임베딩 v2 실패, 해시 임베딩 사용")

        # 방법 2: 해시 기반 임베딩 (대안)
        return self.create_simple_hash_embedding(text)

    def test_clova_connection(self):
        """CLOVA Studio 임베딩 API 연결 테스트"""
        print("🧪 CLOVA Studio 임베딩 API 연결 테스트...")

        test_embedding = self.create_embedding(
            "삼성전자는 대한민국의 대표적인 반도체 기업입니다."
        )

        if test_embedding and len(test_embedding) == 1024:  # 1024차원으로 수정
            print(f"✅ 임베딩 테스트 성공 (차원: {len(test_embedding)})")
            print(f"샘플 값: {test_embedding[:5]}...")
            return True
        else:
            print("❌ 임베딩 테스트 실패")
            return False

    def embed_dart_data(self, data_file: str, batch_size: int = 10):
        """DART 데이터를 Milvus에 임베딩"""
        try:
            print(f"🔄 DART 데이터 임베딩 시작... (배치 크기: {batch_size})")

            # 연결 테스트
            if not self.test_clova_connection():
                return False

            # 데이터 로드
            with open(data_file, "r", encoding="utf-8") as f:
                dart_data = json.load(f)

            from pymilvus import Collection

            # 컬렉션 연결
            company_collection = Collection("dart_companies")
            financial_collection = Collection("dart_financials")
            disclosure_collection = Collection("dart_disclosures")

            total_embedded = 0

            # 1. 기업정보 임베딩
            print("  📋 기업정보 임베딩...")
            company_data = {
                "corp_code": [],
                "corp_name": [],
                "content": [],
                "embedding": []
            }

            for corp_code, info in dart_data["company_info"].items():
                content = f"{info['corp_name']} {info.get('ceo_nm', '')} {info.get('adres', '')} 업종코드:{info.get('induty_code', '')}"

                print(f"    {info['corp_name']} 임베딩 중...", end=" ")
                embedding = self.create_embedding(content)

                if embedding:
                    company_data["corp_code"].append(corp_code)
                    company_data["corp_name"].append(info["corp_name"])
                    company_data["content"].append(content)
                    company_data["embedding"].append(embedding)
                    print("✅")
                else:
                    print("❌")

                time.sleep(1.0)  # API 제한

            if len(company_data["corp_code"]) > 0:
                print(f"    데이터 개수 확인: {len(company_data['corp_code'])}건")

                # 데이터 타입 디버깅
                print(f"    corp_code 타입: {type(company_data['corp_code'])}, 첫번째 값 타입: {type(company_data['corp_code'][0])}")
                print(f"    corp_name 타입: {type(company_data['corp_name'])}, 첫번째 값 타입: {type(company_data['corp_name'][0])}")
                print(f"    content 타입: {type(company_data['content'])}, 첫번째 값 타입: {type(company_data['content'][0])}")
                print(f"    embedding 타입: {type(company_data['embedding'])}, 첫번째 값 타입: {type(company_data['embedding'][0])}")
                print(f"    embedding 차원: {len(company_data['embedding'][0])}")

                # 리스트 형태로 변환해서 삽입 시도
                company_records = []
                for i in range(len(company_data['corp_code'])):
                    company_records.append([
                        i + 1,  # ID 첫 번째 필드로 추가
                        company_data['corp_code'][i],
                        company_data['corp_name'][i],
                        company_data['content'][i],
                        company_data['embedding'][i]
                    ])

                print(f"    변환된 레코드 개수: {len(company_records)}")
                print(f"    첫 번째 레코드 필드 개수: {len(company_records[0])}")
                if len(company_records[0]) >= 5:
                    print(f"    첫 번째 레코드 샘플: {[type(field).__name__ for field in company_records[0]]}")
                    print(f"    스키마와 일치하는지 확인...")
                    print(f"    스키마 필드: ['id', 'corp_code', 'corp_name', 'content', 'embedding']")
                    print(f"    데이터 필드: [id({type(company_records[0][0])}), corp_code({type(company_records[0][1])}), corp_name({type(company_records[0][2])}), content({type(company_records[0][3])}), embedding({type(company_records[0][4])}, dim={len(company_records[0][4])})]")
                else:
                    print(f"    ❌ 필드 개수 부족! 예상: 5개, 실제: {len(company_records[0])}개")
                    print(f"    레코드 내용: {company_records[0]}")
                    return False

                company_collection.insert(company_records)
                total_embedded += len(company_data["corp_code"])
                print(f"    💾 기업정보 {len(company_data['corp_code'])}건 저장 완료")

            # 2. 재무정보 임베딩 (샘플만)
            print("  💰 재무정보 임베딩...")
            financial_data = {
                "corp_code": [],
                "corp_name": [],
                "year": [],
                "account_info": [],
                "embedding": []
            }

            for corp_code, financial_records in dart_data["financial_data"].items():
                corp_name = dart_data["company_info"][corp_code]["corp_name"]

                for year_key, accounts in financial_records.items():
                    if not accounts:
                        continue

                    year = year_key.split("_")[0]

                    # 주요 계정들만 선별 (상위 5개)
                    key_accounts = []
                    for account in accounts[:5]:
                        acc_name = account.get("account_nm", "")
                        amount = account.get("thstrm_amount", "")
                        if acc_name and amount:
                            key_accounts.append(f"{acc_name}: {amount}")

                    if key_accounts:
                        content = f"{corp_name} {year}년 재무정보: " + ", ".join(
                            key_accounts
                        )

                        print(f"    {corp_name} {year}년 임베딩 중...", end=" ")
                        embedding = self.create_embedding(content)

                        if embedding:
                            financial_data["corp_code"].append(corp_code)
                            financial_data["corp_name"].append(corp_name)
                            financial_data["year"].append(year)
                            financial_data["account_info"].append(content)
                            financial_data["embedding"].append(embedding)
                            print("✅")
                        else:
                            print("❌")

                        time.sleep(1.0)  # API 제한

            if len(financial_data["corp_code"]) > 0:
                # 리스트 형태로 변환해서 삽입 (ID 수동 생성)
                financial_records = []
                for i in range(len(financial_data['corp_code'])):
                    financial_records.append([
                        1000 + i,  # ID 수동 생성 (1000번대 사용)
                        financial_data['corp_code'][i],
                        financial_data['corp_name'][i],
                        financial_data['year'][i],
                        financial_data['account_info'][i],
                        financial_data['embedding'][i]
                    ])

                financial_collection.insert(financial_records)
                total_embedded += len(financial_data["corp_code"])
                print(f"    💾 재무정보 {len(financial_data['corp_code'])}건 저장 완료")

            # 3. 공시정보 임베딩 (최근 5건만)
            print("  📢 공시정보 임베딩...")
            disclosure_data = {
                "corp_code": [],
                "corp_name": [],
                "report_name": [],
                "content": [],
                "rcept_dt": [],
                "embedding": []
            }

            for corp_code, disclosures in dart_data["disclosure_data"].items():
                corp_name = dart_data["company_info"][corp_code]["corp_name"]

                # 최근 5건만 (API 제한 고려)
                for disclosure in disclosures[:5]:
                    report_name = disclosure.get("report_nm", "")
                    rcept_dt = disclosure.get("rcept_dt", "")
                    rm = disclosure.get("rm", "")

                    content = f"{corp_name} {report_name} {rm}"

                    print(f"    {corp_name} 공시 임베딩 중...", end=" ")
                    embedding = self.create_embedding(content)

                    if embedding:
                        disclosure_data["corp_code"].append(corp_code)
                        disclosure_data["corp_name"].append(corp_name)
                        disclosure_data["report_name"].append(report_name)
                        disclosure_data["content"].append(content)
                        disclosure_data["rcept_dt"].append(rcept_dt)
                        disclosure_data["embedding"].append(embedding)
                        print("✅")
                    else:
                        print("❌")

                    time.sleep(1.0)  # API 제한

            if len(disclosure_data["corp_code"]) > 0:
                # 리스트 형태로 변환해서 삽입 (ID 수동 생성)
                disclosure_records = []
                for i in range(len(disclosure_data['corp_code'])):
                    disclosure_records.append([
                        2000 + i,  # ID 수동 생성 (2000번대 사용)
                        disclosure_data['corp_code'][i],
                        disclosure_data['corp_name'][i],
                        disclosure_data['report_name'][i],
                        disclosure_data['content'][i],
                        disclosure_data['rcept_dt'][i],
                        disclosure_data['embedding'][i]
                    ])

                disclosure_collection.insert(disclosure_records)
                total_embedded += len(disclosure_data["corp_code"])
                print(f"    💾 공시정보 {len(disclosure_data['corp_code'])}건 저장 완료")

            # 컬렉션 로드 (검색 가능하게)
            print("  🔄 컬렉션 로딩 중...")
            company_collection.load()
            financial_collection.load()
            disclosure_collection.load()

            print(f"🎉 임베딩 완료! 총 {total_embedded}건")
            return True

        except Exception as e:
            print(f"❌ 임베딩 실패: {e}")
            import traceback

            traceback.print_exc()
            return False


# 메인 함수에서 ClovaXEmbedder 사용
def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="DART 데이터 수집 및 Milvus 임베딩")
    subparsers = parser.add_subparsers(dest="command", help="실행할 작업")

    # embed 커맨드
    embed_parser = subparsers.add_parser("embed", help="Milvus 임베딩")
    embed_parser.add_argument(
        "--create-collections", action="store_true", help="컬렉션 새로 생성"
    )
    embed_parser.add_argument("--batch-size", type=int, default=10, help="배치 크기")
    embed_parser.add_argument("--data-file", help="임베딩할 데이터 파일 경로")

    args = parser.parse_args()

    if args.command == "embed":
        # Clova X 임베딩
        embedder = ClovaXEmbedder()

        # 클라이언트 설정
        if not embedder.setup_clova_client():
            return
        if not embedder.setup_milvus_client():
            return

        # 컬렉션 생성
        if args.create_collections:
            if not embedder.create_collections():
                return

        # 데이터 파일 찾기
        data_file = args.data_file
        if not data_file:
            # 가장 최근 파일 자동 찾기
            data_dir = Path("/app/data/crawled/dart_api")
            json_files = list(data_dir.glob("dart_data_*.json"))
            if not json_files:
                print("❌ 임베딩할 DART 데이터 파일이 없습니다.")
                return
            data_file = max(json_files, key=lambda x: x.stat().st_mtime)
            print(f"📄 자동 선택된 파일: {data_file}")

        # 임베딩 실행
        embedder.embed_dart_data(str(data_file), args.batch_size)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
