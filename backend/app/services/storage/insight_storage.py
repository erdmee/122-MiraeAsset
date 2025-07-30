# app/services/insight_storage.py

from typing import Dict, List, Optional
from datetime import datetime
import json
import hashlib
import logging

from app.services.core.db import ElasticsearchConnection

logger = logging.getLogger(__name__)


class InsightStorage:
    """인사이트 저장 및 검색 시스템"""

    def __init__(self):
        self.es_client = ElasticsearchConnection.get_client()
        self.index_name = "insights"
        if self.es_client is not None:
            self._ensure_index_exists()

    def _ensure_index_exists(self):
        """인사이트 인덱스 생성"""
        if self.es_client and not self.es_client.indices.exists(index=self.index_name):
            mapping = {
                "mappings": {
                    "properties": {
                        "title": {
                            "type": "text",
                            "analyzer": "standard",
                            "fields": {"keyword": {"type": "keyword"}},
                        },
                        "content": {"type": "text", "analyzer": "standard"},
                        "content_chunks": {"type": "text", "analyzer": "standard"},
                        "summary": {"type": "text", "analyzer": "standard"},
                        "created_at": {"type": "date"},
                        "user_id": {"type": "keyword"},
                        "query": {"type": "text", "analyzer": "standard"},
                        "entities": {"type": "keyword"},
                        "tags": {"type": "keyword"},
                        "insight_type": {"type": "keyword"},
                        "embedding": {"type": "dense_vector", "dims": 1024},
                        "metadata": {
                            "type": "object",
                            "properties": {
                                "graph_rag_used": {"type": "boolean"},
                                "data_sources": {"type": "keyword"},
                                "confidence_score": {"type": "float"},
                            },
                        },
                    }
                }
            }

            self.es_client.indices.create(index=self.index_name, body=mapping)
            logger.info(f"인사이트 인덱스 '{self.index_name}' 생성 완료")

    async def store_insight(
        self,
        insight_content: str,
        user_query: str,
        user_id: str = "default",
        entities: List[str] = None,
        metadata: Dict = None,
    ) -> str:
        """인사이트 저장"""

        if self.es_client is None:
            logger.warning("Elasticsearch 연결 없음 - 인사이트 저장 불가")
            return "no-elasticsearch-connection"

        # 제목 생성 (첫 줄 또는 요약)
        title = self._generate_title(insight_content, user_query)

        # 내용 청킹
        chunks = self._chunk_content(insight_content)

        # 요약 생성
        summary = self._generate_summary(insight_content)

        # 엔티티 추출 (제공되지 않은 경우)
        if not entities:
            entities = self._extract_entities(insight_content)

        # 태그 생성
        tags = self._generate_tags(insight_content, user_query, entities)

        # 임베딩 생성 (더미 구현)
        embedding = self._generate_embedding(insight_content)

        # 문서 ID 생성
        doc_id = self._generate_doc_id(user_query, user_id, insight_content)

        # 문서 생성
        doc = {
            "title": title,
            "content": insight_content,
            "content_chunks": chunks,
            "summary": summary,
            "created_at": datetime.now(),
            "user_id": user_id,
            "query": user_query,
            "entities": entities or [],
            "tags": tags,
            "insight_type": self._classify_insight_type(insight_content),
            "embedding": embedding,
            "metadata": metadata or {},
        }

        # Elasticsearch에 저장
        try:
            response = self.es_client.index(index=self.index_name, id=doc_id, body=doc)
            logger.info(f"인사이트 저장 완료: {doc_id}")
            return doc_id
        except Exception as e:
            logger.error(f"인사이트 저장 실패: {e}")
            raise

    def _generate_title(self, content: str, query: str) -> str:
        """제목 생성"""
        # 첫 번째 줄에서 제목 추출 시도
        lines = content.split("\n")
        for line in lines:
            if line.strip() and not line.startswith("#"):
                title = line.strip()[:100]
                if title:
                    return title

        # 쿼리 기반 제목 생성
        return f"{query[:50]}... 분석 결과"

    def _chunk_content(self, content: str, chunk_size: int = 500) -> List[str]:
        """내용 청킹"""
        chunks = []
        paragraphs = content.split("\n\n")

        current_chunk = ""
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) > chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = paragraph
            else:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _generate_summary(self, content: str) -> str:
        """요약 생성"""
        # 간단한 요약 (첫 200자)
        clean_content = " ".join(content.split())
        return (
            clean_content[:200] + "..." if len(clean_content) > 200 else clean_content
        )

    def _extract_entities(self, content: str) -> List[str]:
        """엔티티 추출"""
        entities = []

        # 기본 금융 엔티티들
        financial_entities = [
            "삼성전자",
            "SK하이닉스",
            "LG화학",
            "현대차",
            "네이버",
            "카카오",
            "비트코인",
            "암호화폐",
            "반도체",
            "AI",
            "전기차",
            "배터리",
            "코스피",
            "코스닥",
            "기준금리",
            "환율",
            "인플레이션",
        ]

        for entity in financial_entities:
            if entity in content:
                entities.append(entity)

        return list(set(entities))

    def _generate_tags(
        self, content: str, query: str, entities: List[str]
    ) -> List[str]:
        """태그 생성"""
        tags = []

        # 엔티티 기반 태그
        tags.extend(entities)

        # 내용 기반 태그
        content_lower = content.lower()

        if (
            "투자" in content_lower
            or "매수" in content_lower
            or "매도" in content_lower
        ):
            tags.append("투자추천")

        if "위험" in content_lower or "리스크" in content_lower:
            tags.append("위험분석")

        if "전망" in content_lower or "예상" in content_lower:
            tags.append("시장전망")

        if "뉴스" in content_lower or "이슈" in content_lower:
            tags.append("시장이슈")

        if "기술" in content_lower or "혁신" in content_lower:
            tags.append("기술분석")

        return list(set(tags))

    def _classify_insight_type(self, content: str) -> str:
        """인사이트 유형 분류"""
        content_lower = content.lower()

        if "개별" in content_lower or "기업" in content_lower:
            return "individual_stock"
        elif "시장" in content_lower or "전체" in content_lower:
            return "market_analysis"
        elif "섹터" in content_lower or "업종" in content_lower:
            return "sector_analysis"
        elif "포트폴리오" in content_lower:
            return "portfolio"
        else:
            return "general"

    def _generate_embedding(self, content: str) -> List[float]:
        """HyperCLOVA X를 사용한 실제 임베딩 생성"""
        try:
            from app.services.external.hyperclova_client import MultiLLMClient

            # HyperCLOVA X 클라이언트 초기화
            llm_client = MultiLLMClient()

            if not llm_client.is_available():
                logger.warning(
                    "HyperCLOVA X 클라이언트를 사용할 수 없습니다 - 더미 임베딩 사용"
                )
                # 폴백: 더미 벡터 (1024차원)
                import random

                return [random.random() for _ in range(1024)]

            # 텍스트 전처리 (길이 제한)
            # HyperCLOVA X 임베딩 API의 최대 길이에 맞춰 조정
            if len(content) > 2000:
                # 앞부분과 뒷부분을 조합하여 요약
                content = content[:1000] + "..." + content[-1000:]

            # HyperCLOVA X 임베딩 생성
            embedding = llm_client.create_embedding(content)

            if embedding and len(embedding) > 0:
                logger.info(f"HyperCLOVA X 임베딩 생성 성공 (차원: {len(embedding)})")

                # 1024차원으로 맞추기 (필요시 패딩 또는 잘라내기)
                if len(embedding) > 1024:
                    embedding = embedding[:1024]
                elif len(embedding) < 1024:
                    # 부족한 차원은 0으로 패딩
                    embedding.extend([0.0] * (1024 - len(embedding)))

                return embedding
            else:
                logger.warning("HyperCLOVA X 임베딩 생성 실패 - 더미 임베딩 사용")
                # 폴백: 더미 벡터
                import random

                return [random.random() for _ in range(1024)]

        except Exception as e:
            logger.error(f"임베딩 생성 중 오류: {e}")
            # 폴백: 더미 벡터
            import random

            return [random.random() for _ in range(1024)]

    def _generate_doc_id(self, query: str, user_id: str, content: str) -> str:
        """문서 ID 생성"""
        combined = f"{user_id}:{query}:{content[:100]}"
        return hashlib.md5(combined.encode()).hexdigest()

    async def search_insights(
        self,
        query: str,
        user_id: str = None,
        entities: List[str] = None,
        tags: List[str] = None,
        limit: int = 10,
    ) -> List[Dict]:
        """인사이트 검색"""

        if self.es_client is None:
            logger.warning("Elasticsearch 연결 없음 - 인사이트 검색 불가")
            return []

        # 검색 쿼리 구성
        must_queries = [
            {
                "multi_match": {
                    "query": query,
                    "fields": ["title^3", "content^2", "summary", "content_chunks"],
                    "type": "best_fields",
                }
            }
        ]

        # 필터 조건
        filter_queries = []

        if user_id:
            filter_queries.append({"term": {"user_id": user_id}})

        if entities:
            filter_queries.append({"terms": {"entities": entities}})

        if tags:
            filter_queries.append({"terms": {"tags": tags}})

        # 검색 실행
        search_body = {
            "query": {"bool": {"must": must_queries, "filter": filter_queries}},
            "highlight": {"fields": {"content": {}, "title": {}}},
            "sort": [{"created_at": {"order": "desc"}}],
            "size": limit,
        }

        try:
            response = self.es_client.search(index=self.index_name, body=search_body)

            results = []
            for hit in response["hits"]["hits"]:
                result = {
                    "id": hit["_id"],
                    "score": hit["_score"],
                    "title": hit["_source"]["title"],
                    "summary": hit["_source"]["summary"],
                    "created_at": hit["_source"]["created_at"],
                    "entities": hit["_source"]["entities"],
                    "tags": hit["_source"]["tags"],
                    "insight_type": hit["_source"]["insight_type"],
                    "highlights": hit.get("highlight", {}),
                }
                results.append(result)

            logger.info(f"인사이트 검색 완료: {len(results)}건")
            return results

        except Exception as e:
            logger.error(f"인사이트 검색 실패: {e}")
            return []

    async def get_insight_by_id(self, doc_id: str) -> Optional[Dict]:
        """ID로 인사이트 조회"""
        if self.es_client is None:
            logger.warning("Elasticsearch 연결 없음 - 인사이트 조회 불가")
            return None

        try:
            response = self.es_client.get(index=self.index_name, id=doc_id)
            return response["_source"]
        except Exception as e:
            logger.error(f"인사이트 조회 실패: {e}")
            return None

    async def get_user_insights(self, user_id: str, limit: int = 20) -> List[Dict]:
        """사용자별 인사이트 목록"""
        return await self.search_insights("", user_id=user_id, limit=limit)

    async def get_insights_by_entities(
        self, entities: List[str], limit: int = 10
    ) -> List[Dict]:
        """엔티티별 인사이트 검색"""
        return await self.search_insights("", entities=entities, limit=limit)
