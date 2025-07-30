from elasticsearch import Elasticsearch, helpers
from elasticsearch.exceptions import NotFoundError, RequestError
import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class ElasticVectorDB:
    def __init__(self, host=None, port=None, index_name="documents"):
        self.host = host or os.getenv("ELASTICSEARCH_HOST", "elasticsearch")
        self.port = port or int(os.getenv("ELASTICSEARCH_PORT", 9200))
        self.index_name = index_name

        try:
            # Elasticsearch 8.x 스타일로 연결
            self.es = Elasticsearch(
                [{"host": self.host, "port": self.port, "scheme": "http"}],
                timeout=30,
                max_retries=3,
                retry_on_timeout=True,
            )

            # 연결 테스트
            if self.es.ping():
                logger.info(f"Elasticsearch 연결 성공: {self.host}:{self.port}")
                self._ensure_index()
            else:
                logger.error("Elasticsearch 연결 실패")
                self.es = None

        except Exception as e:
            logger.error(f"Elasticsearch 초기화 실패: {e}")
            self.es = None

    def _ensure_index(self):
        """인덱스 생성 및 매핑 설정"""
        if not self.es:
            return

        try:
            if not self.es.indices.exists(index=self.index_name):
                # 벡터 차원 환경변수에서 가져오기
                vector_dims = int(os.getenv("VECTOR_DIMENSIONS", 768))

                mapping = {
                    "mappings": {
                        "properties": {
                            "embedding": {
                                "type": "dense_vector",
                                "dims": vector_dims,
                                "index": True,
                                "similarity": "cosine",
                            },
                            "text": {"type": "text", "analyzer": "korean"},
                            "title": {"type": "text", "analyzer": "korean"},
                            "summary": {"type": "text", "analyzer": "korean"},
                            "doc_id": {"type": "keyword"},
                            "doc_type": {"type": "keyword"},
                            "date": {"type": "date"},
                            "meta": {
                                "type": "object",
                                "properties": {
                                    "source": {"type": "keyword"},
                                    "category": {"type": "keyword"},
                                    "company": {"type": "keyword"},
                                    "sector": {"type": "keyword"},
                                },
                            },
                            "timestamp": {"type": "date"},
                        }
                    },
                    "settings": {
                        "number_of_shards": 1,
                        "number_of_replicas": 0,
                        "analysis": {
                            "analyzer": {
                                "korean": {
                                    "type": "custom",
                                    "tokenizer": "standard",
                                    "filter": ["lowercase", "cjk_width"],
                                }
                            }
                        },
                    },
                }

                self.es.indices.create(index=self.index_name, body=mapping)
                logger.info(f"Elasticsearch 인덱스 생성됨: {self.index_name}")

        except Exception as e:
            logger.error(f"인덱스 생성 실패: {e}")

    def insert(self, docs: List[Dict]) -> bool:
        """문서 벌크 삽입"""
        if not self.es:
            logger.warning("Elasticsearch 연결 없음")
            return False

        try:
            actions = []
            for doc in docs:
                action = {
                    "_index": self.index_name,
                    "_id": doc.get("doc_id"),  # doc_id가 있으면 사용
                    "_source": doc,
                }
                actions.append(action)

            # 벌크 삽입 실행
            success_count, errors = helpers.bulk(
                self.es,
                actions,
                refresh=True,  # 즉시 검색 가능하도록
                request_timeout=60,
            )

            logger.info(f"문서 삽입 완료: {success_count}개 성공")
            if errors:
                logger.warning(f"삽입 중 {len(errors)}개 오류 발생")

            return True

        except Exception as e:
            logger.error(f"문서 삽입 실패: {e}")
            return False

    def search(
        self, query_vector: List[float], top_k: int = 5, filters: Dict = None
    ) -> List[Dict]:
        """벡터 유사도 검색"""
        if not self.es:
            logger.warning("Elasticsearch 연결 없음 - 더미 결과 반환")
            return self._get_dummy_results(top_k)

        try:
            # 기본 벡터 검색 쿼리
            search_body = {
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
            if filters:
                filter_queries = []
                for key, value in filters.items():
                    if key in ["doc_type", "doc_id"]:
                        filter_queries.append({"term": {key: value}})
                    elif key.startswith("meta."):
                        filter_queries.append({"term": {key: value}})
                    elif key == "date_range":
                        filter_queries.append(
                            {
                                "range": {
                                    "date": {
                                        "gte": value.get("start"),
                                        "lte": value.get("end"),
                                    }
                                }
                            }
                        )

                if filter_queries:
                    search_body["query"]["script_score"]["query"] = {
                        "bool": {"filter": filter_queries}
                    }

            # 검색 실행
            res = self.es.search(index=self.index_name, body=search_body)

            # 결과 포맷팅
            results = []
            for hit in res["hits"]["hits"]:
                result = {
                    "id": hit["_id"],
                    "score": hit["_score"],
                    "source": hit["_source"],
                }
                results.append(result)

            logger.info(f"벡터 검색 완료: {len(results)}개 결과")
            return results

        except Exception as e:
            logger.error(f"벡터 검색 실패: {e}")
            return self._get_dummy_results(top_k)

    def text_search(
        self, query: str, top_k: int = 5, filters: Dict = None
    ) -> List[Dict]:
        """텍스트 검색 (BM25)"""
        if not self.es:
            return self._get_dummy_results(top_k)

        try:
            search_body = {
                "size": top_k,
                "query": {
                    "bool": {
                        "should": [
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["text^2", "title^3", "summary^1.5"],
                                    "type": "best_fields",
                                    "fuzziness": "AUTO",
                                }
                            },
                            {"match_phrase": {"text": {"query": query, "boost": 2}}},
                        ],
                        "minimum_should_match": 1,
                    }
                },
                "highlight": {"fields": {"text": {}, "title": {}, "summary": {}}},
            }

            # 필터 추가 (벡터 검색과 동일)
            if filters:
                filter_queries = []
                for key, value in filters.items():
                    if key in ["doc_type", "doc_id"]:
                        filter_queries.append({"term": {key: value}})
                    elif key.startswith("meta."):
                        filter_queries.append({"term": {key: value}})

                if filter_queries:
                    search_body["query"]["bool"]["filter"] = filter_queries

            res = self.es.search(index=self.index_name, body=search_body)

            results = []
            for hit in res["hits"]["hits"]:
                result = {
                    "id": hit["_id"],
                    "score": hit["_score"],
                    "source": hit["_source"],
                    "highlight": hit.get("highlight", {}),
                }
                results.append(result)

            logger.info(f"텍스트 검색 완료: {len(results)}개 결과")
            return results

        except Exception as e:
            logger.error(f"텍스트 검색 실패: {e}")
            return self._get_dummy_results(top_k)

    def delete_by_doc_id(self, doc_id: str) -> bool:
        """문서 ID로 삭제"""
        if not self.es:
            return False

        try:
            self.es.delete(index=self.index_name, id=doc_id, ignore=[404])
            logger.info(f"문서 삭제 완료: {doc_id}")
            return True
        except Exception as e:
            logger.error(f"문서 삭제 실패: {e}")
            return False

    def get_stats(self) -> Dict:
        """인덱스 통계 정보"""
        if not self.es:
            return {"error": "Elasticsearch 연결 없음"}

        try:
            stats = self.es.indices.stats(index=self.index_name)
            return {
                "total_docs": stats["indices"][self.index_name]["total"]["docs"][
                    "count"
                ],
                "index_size": stats["indices"][self.index_name]["total"]["store"][
                    "size_in_bytes"
                ],
                "status": "healthy",
            }
        except Exception as e:
            logger.error(f"통계 조회 실패: {e}")
            return {"error": str(e)}

    def _get_dummy_results(self, top_k: int) -> List[Dict]:
        """더미 검색 결과"""
        return [
            {
                "id": f"dummy_{i}",
                "score": 0.9 - (i * 0.1),
                "source": {
                    "text": f"더미 문서 {i} 내용",
                    "doc_id": f"dummy_{i}",
                    "doc_type": "dummy",
                },
            }
            for i in range(min(top_k, 3))
        ]


# 하위 호환성을 위한 별칭
VectorQueryTool = ElasticVectorDB
