import logging
from typing import List, Dict, Any, Optional
from app.services.core.db import ElasticsearchConnection
from app.config import settings

logger = logging.getLogger(__name__)


class ElasticsearchQueryTool:
    """Elasticsearch 벡터 검색 및 텍스트 검색 도구"""

    def __init__(self):
        self.es = ElasticsearchConnection.get_client()
        self.index_name = settings.ELASTICSEARCH_INDEX_NAME

    def vector_search(
        self,
        query_vector: List[float],
        top_k: int = None,
        filter_type: Optional[str] = None,
        corp_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """벡터 유사도 기반 검색"""
        if top_k is None:
            top_k = settings.DEFAULT_TOP_K

        # 벡터 검색 쿼리 구성
        query = {
            "size": top_k,
            "query": {
                "script_score": {
                    "query": {"match_all": {}},
                    "script": {
                        "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                        "params": {"query_vector": query_vector},
                    },
                }
            },
        }

        # 필터 추가
        if filter_type or corp_name:
            must_filters = []
            if filter_type:
                must_filters.append({"term": {"type": filter_type}})
            if corp_name:
                must_filters.append({"term": {"corp_name.keyword": corp_name}})

            query["query"]["script_score"]["query"] = {"bool": {"must": must_filters}}

        try:
            response = self.es.search(index=self.index_name, body=query)

            results = []
            for hit in response["hits"]["hits"]:
                source = hit["_source"]
                results.append(
                    {
                        "id": hit["_id"],
                        "score": hit["_score"],
                        "type": source.get("type"),
                        "corp_name": source.get("corp_name"),
                        "content": source.get("content"),
                        "corp_code": source.get("corp_code"),
                        "year": source.get("year"),
                        "report_name": source.get("report_name"),
                        "rcept_dt": source.get("rcept_dt"),
                    }
                )

            logger.info(f"벡터 검색 완료: {len(results)}건 검색됨")
            return results

        except Exception as e:
            logger.error(f"벡터 검색 실패: {e}")
            return []

    def text_search(
        self,
        query_text: str,
        top_k: int = None,
        filter_type: Optional[str] = None,
        corp_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """텍스트 기반 검색 (키워드 매칭)"""
        if top_k is None:
            top_k = settings.DEFAULT_TOP_K

        # 텍스트 검색 쿼리 구성
        query = {
            "size": top_k,
            "query": {
                "bool": {
                    "should": [
                        {"match": {"content": {"query": query_text, "boost": 2.0}}},
                        {"match": {"corp_name": {"query": query_text, "boost": 1.5}}},
                        {"match": {"report_name": {"query": query_text, "boost": 1.0}}},
                    ]
                }
            },
        }

        # 필터 추가
        if filter_type or corp_name:
            must_filters = []
            if filter_type:
                must_filters.append({"term": {"type": filter_type}})
            if corp_name:
                must_filters.append({"term": {"corp_name.keyword": corp_name}})

            query["query"]["bool"]["must"] = must_filters

        try:
            response = self.es.search(index=self.index_name, body=query)

            results = []
            for hit in response["hits"]["hits"]:
                source = hit["_source"]
                results.append(
                    {
                        "id": hit["_id"],
                        "score": hit["_score"],
                        "type": source.get("type"),
                        "corp_name": source.get("corp_name"),
                        "content": source.get("content"),
                        "corp_code": source.get("corp_code"),
                        "year": source.get("year"),
                        "report_name": source.get("report_name"),
                        "rcept_dt": source.get("rcept_dt"),
                    }
                )

            logger.info(f"텍스트 검색 완료: {len(results)}건 검색됨")
            return results

        except Exception as e:
            logger.error(f"텍스트 검색 실패: {e}")
            return []

    def hybrid_search(
        self,
        query_text: str,
        query_vector: List[float],
        top_k: int = None,
        text_weight: float = 0.3,
        vector_weight: float = 0.7,
        filter_type: Optional[str] = None,
        corp_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """하이브리드 검색 (텍스트 + 벡터)"""
        if top_k is None:
            top_k = settings.DEFAULT_TOP_K

        # 텍스트 검색 결과
        text_results = self.text_search(query_text, top_k * 2, filter_type, corp_name)
        # 벡터 검색 결과
        vector_results = self.vector_search(
            query_vector, top_k * 2, filter_type, corp_name
        )

        # 결과 통합 및 스코어 조합
        combined_results = {}

        for result in text_results:
            doc_id = result["id"]
            combined_results[doc_id] = result.copy()
            combined_results[doc_id]["combined_score"] = result["score"] * text_weight
            combined_results[doc_id]["text_score"] = result["score"]
            combined_results[doc_id]["vector_score"] = 0.0

        for result in vector_results:
            doc_id = result["id"]
            if doc_id in combined_results:
                combined_results[doc_id]["combined_score"] += (
                    result["score"] * vector_weight
                )
                combined_results[doc_id]["vector_score"] = result["score"]
            else:
                combined_results[doc_id] = result.copy()
                combined_results[doc_id]["combined_score"] = (
                    result["score"] * vector_weight
                )
                combined_results[doc_id]["text_score"] = 0.0
                combined_results[doc_id]["vector_score"] = result["score"]

        # 통합 스코어로 정렬
        final_results = sorted(
            combined_results.values(), key=lambda x: x["combined_score"], reverse=True
        )[:top_k]

        logger.info(f"하이브리드 검색 완료: {len(final_results)}건 검색됨")
        return final_results

    def get_companies(self) -> List[str]:
        """등록된 기업 목록 조회"""
        try:
            query = {
                "size": 0,
                "aggs": {
                    "companies": {"terms": {"field": "corp_name.keyword", "size": 100}}
                },
            }

            response = self.es.search(index=self.index_name, body=query)
            companies = [
                bucket["key"]
                for bucket in response["aggregations"]["companies"]["buckets"]
            ]

            logger.info(f"기업 목록 조회: {len(companies)}개 기업")
            return companies

        except Exception as e:
            logger.error(f"기업 목록 조회 실패: {e}")
            return []

    def get_document_types(self) -> List[str]:
        """문서 타입 목록 조회"""
        try:
            query = {
                "size": 0,
                "aggs": {"types": {"terms": {"field": "type", "size": 10}}},
            }

            response = self.es.search(index=self.index_name, body=query)
            types = [
                bucket["key"] for bucket in response["aggregations"]["types"]["buckets"]
            ]

            logger.info(f"문서 타입 조회: {types}")
            return types

        except Exception as e:
            logger.error(f"문서 타입 조회 실패: {e}")
            return []


# Agent에서 사용할 수 있도록 간단한 래퍼 함수들
def search_financial_documents(
    query: str,
    search_type: str = "hybrid",  # "text", "vector", "hybrid"
    top_k: int = 5,
    filter_type: Optional[str] = None,
    corp_name: Optional[str] = None,
) -> str:
    """Agent가 사용할 수 있는 금융 문서 검색 함수"""

    tool = ElasticsearchQueryTool()

    try:
        if search_type == "text":
            results = tool.text_search(query, top_k, filter_type, corp_name)
        elif search_type == "vector":
            # HyperCLOVA X로 실제 임베딩 생성
            query_vector = _generate_query_embedding(query)
            if query_vector:
                results = tool.vector_search(
                    query_vector, top_k, filter_type, corp_name
                )
            else:
                # 임베딩 생성 실패 시 텍스트 검색으로 폴백
                logger.warning("임베딩 생성 실패 - 텍스트 검색으로 폴백")
                results = tool.text_search(query, top_k, filter_type, corp_name)
        else:  # hybrid
            # 하이브리드: 벡터 검색과 텍스트 검색 결과 결합
            query_vector = _generate_query_embedding(query)
            if query_vector:
                vector_results = tool.vector_search(
                    query_vector, top_k // 2 + 1, filter_type, corp_name
                )
                text_results = tool.text_search(
                    query, top_k // 2 + 1, filter_type, corp_name
                )

                # 결과 합치기 (중복 제거)
                seen_ids = set()
                results = []
                for result in vector_results + text_results:
                    if result["id"] not in seen_ids:
                        seen_ids.add(result["id"])
                        results.append(result)

                # top_k 개수로 제한
                results = results[:top_k]
            else:
                # 임베딩 생성 실패 시 텍스트 검색만 사용
                logger.warning("임베딩 생성 실패 - 텍스트 검색만 사용")
                results = tool.text_search(query, top_k, filter_type, corp_name)

        if not results:
            return f"'{query}'에 대한 검색 결과가 없습니다."

        # 결과를 텍스트로 포맷팅
        formatted_results = []
        for i, result in enumerate(results, 1):
            content = (
                result["content"][:200] + "..."
                if len(result["content"]) > 200
                else result["content"]
            )

            formatted_result = f"{i}. [{result['type']}] {result['corp_name']}"
            if result.get("year"):
                formatted_result += f" ({result['year']}년)"
            if result.get("report_name"):
                formatted_result += f" - {result['report_name']}"
            if result.get("score"):
                formatted_result += f" (유사도: {result['score']:.3f})"
            formatted_result += f"\n   내용: {content}\n"

            formatted_results.append(formatted_result)

        return f"검색 결과 ({len(results)}건):\n\n" + "\n".join(formatted_results)

    except Exception as e:
        logger.error(f"금융 문서 검색 실패: {e}")
        return f"검색 중 오류가 발생했습니다: {str(e)}"


def _generate_query_embedding(query: str) -> Optional[List[float]]:
    """쿼리를 위한 HyperCLOVA X 임베딩 생성"""
    try:
        from app.services.external.hyperclova_client import MultiLLMClient

        llm_client = MultiLLMClient()

        if not llm_client.is_available():
            logger.warning("HyperCLOVA X 클라이언트를 사용할 수 없습니다")
            return None

        # HyperCLOVA X 임베딩 생성
        embedding = llm_client.create_embedding(query)

        if embedding and len(embedding) > 0:
            logger.info(f"쿼리 임베딩 생성 성공 (차원: {len(embedding)})")

            # 1024차원으로 맞추기
            if len(embedding) > 1024:
                embedding = embedding[:1024]
            elif len(embedding) < 1024:
                embedding.extend([0.0] * (1024 - len(embedding)))

            return embedding
        else:
            logger.warning("쿼리 임베딩 생성 실패")
            return None

    except Exception as e:
        logger.error(f"쿼리 임베딩 생성 중 오류: {e}")
        return None


def get_available_companies() -> str:
    """Agent가 사용할 수 있는 기업 목록 조회 함수"""
    tool = ElasticsearchQueryTool()
    companies = tool.get_companies()

    if not companies:
        return "등록된 기업이 없습니다."

    return f"등록된 기업 목록 ({len(companies)}개):\n" + ", ".join(companies)


def get_document_types() -> str:
    """Agent가 사용할 수 있는 문서 타입 조회 함수"""
    tool = ElasticsearchQueryTool()
    types = tool.get_document_types()

    if not types:
        return "등록된 문서 타입이 없습니다."

    return f"문서 타입: {', '.join(types)}"
