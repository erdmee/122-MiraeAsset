# app/services/core/news_to_graph.py

import json
import os
import re
from datetime import datetime
from typing import List, Dict, Any
from app.services.core.db import Neo4jConnection
from app.services.external.hyperclova_client import HyperClovaXClient
import logging

logger = logging.getLogger(__name__)


class NewsToGraphPipeline:
    """뉴스 데이터를 Neo4j Graph DB로 변환하는 파이프라인"""

    def __init__(self):
        self.neo4j = Neo4jConnection()
        self.llm_client = HyperClovaXClient()

    def extract_entities_from_news(self, news_content: str) -> List[str]:
        """뉴스 내용에서 엔티티 추출"""
        try:
            prompt = f"""
다음 뉴스 내용에서 투자와 관련된 주요 엔티티를 추출해주세요.
엔티티 종류: 회사명, 기술명, 산업명, 인물명, 제품명

뉴스 내용:
{news_content}

추출된 엔티티를 콤마로 구분하여 나열해주세요:
"""

            messages = [{"role": "user", "content": prompt}]
            response = self.llm_client.chat_completion(
                messages, max_tokens=200, temperature=0.3
            )

            if response and response.get_content():
                entities_text = response.get_content().strip()
                # 콤마로 분리하고 정리
                entities = [
                    entity.strip()
                    for entity in entities_text.split(",")
                    if entity.strip()
                ]
                return entities[:10]  # 최대 10개까지
            else:
                # 기본 엔티티 추출 (키워드 기반)
                return self._extract_basic_entities(news_content)

        except Exception as e:
            print(f"엔티티 추출 실패: {e}")
            return self._extract_basic_entities(news_content)

    def _extract_basic_entities(self, text: str) -> List[str]:
        """기본 키워드 기반 엔티티 추출"""
        known_entities = [
            "삼성전자",
            "SK하이닉스",
            "네이버",
            "카카오",
            "현대차",
            "LG화학",
            "AI",
            "인공지능",
            "반도체",
            "배터리",
            "전기차",
            "바이오",
            "플랫폼",
            "비트코인",
            "스테이블코인",
            "암호화폐",
            "블록체인",
            "기준금리",
            "환율",
            "코스피",
            "코스닥",
            "실적",
            "배당",
        ]

        found_entities = []
        for entity in known_entities:
            if entity in text:
                found_entities.append(entity)

        return found_entities

    def create_news_graph(self, news_data: List[Dict]) -> bool:
        """뉴스 데이터로 Graph DB 구축"""
        try:
            # Neo4j 연결 확인
            driver = self.neo4j.get_driver()
            if not driver:
                print("Neo4j 연결 실패 - 드라이버가 None입니다")
                return False

            # 연결 테스트
            with driver.session() as test_session:
                test_session.run("RETURN 1")

            with driver.session() as session:
                # 기존 뉴스 노드 삭제 (선택적)
                # session.run("MATCH (n:News) DELETE n")

                for news_item in news_data:
                    try:
                        # 뉴스 엔티티 추출
                        entities = self.extract_entities_from_news(
                            f"{news_item.get('title', '')} {news_item.get('summary', '')}"
                        )

                        # 뉴스 노드 생성
                        news_query = """
                        CREATE (news:News {
                            title: $title,
                            summary: $summary,
                            source: $source,
                            published_at: $published_at,
                            crawled_at: $crawled_at,
                            importance_score: $importance_score,
                            entities_list: $entities_list
                        })
                        RETURN news.title as created_title
                        """

                        session.run(
                            news_query,
                            {
                                "title": news_item.get("title", ""),
                                "summary": news_item.get("summary", ""),
                                "source": news_item.get("source", ""),
                                "published_at": news_item.get("published_at", ""),
                                "crawled_at": datetime.now().isoformat(),
                                "importance_score": news_item.get(
                                    "importance_score", 1.0
                                ),
                                "entities_list": entities,
                            },
                        )

                        # 엔티티별로 노드 생성 및 관계 설정
                        for entity in entities:
                            try:
                                # 엔티티 노드 생성 (이미 존재하면 스킵)
                                entity_query = """
                                MERGE (entity:Entity {name: $entity_name})
                                ON CREATE SET entity.type = $entity_type,
                                             entity.created_at = $created_at
                                RETURN entity.name as entity_name
                                """

                                entity_type = self._classify_entity_type(entity)
                                session.run(
                                    entity_query,
                                    {
                                        "entity_name": entity,
                                        "entity_type": entity_type,
                                        "created_at": datetime.now().isoformat(),
                                    },
                                )

                                # 뉴스-엔티티 관계 생성
                                relation_query = """
                                MATCH (news:News {title: $news_title})
                                MATCH (entity:Entity {name: $entity_name})
                                MERGE (news)-[:MENTIONS]->(entity)
                                """

                                session.run(
                                    relation_query,
                                    {
                                        "news_title": news_item.get("title", ""),
                                        "entity_name": entity,
                                    },
                                )

                            except Exception as entity_e:
                                print(f"엔티티 '{entity}' 처리 실패: {entity_e}")
                                continue

                        print(f"뉴스 저장 완료: {news_item.get('title', '')[:50]}...")

                    except Exception as e:
                        print(f"개별 뉴스 처리 실패: {e}")
                        continue

                # 회사 노드들 간의 관계 생성 (경쟁, 협력 등)
                self._create_company_relationships(session)

                print(f"총 {len(news_data)}개 뉴스의 Graph DB 구축 완료")
                return True

        except Exception as e:
            print(f"Graph DB 구축 실패: {e}")
            return False

    def _classify_entity_type(self, entity: str) -> str:
        """엔티티 타입 분류"""
        company_keywords = ["전자", "하이닉스", "네이버", "카카오", "현대차", "LG화학"]
        tech_keywords = [
            "AI",
            "인공지능",
            "반도체",
            "배터리",
            "전기차",
            "바이오",
            "블록체인",
        ]
        market_keywords = ["코스피", "코스닥", "기준금리", "환율", "실적", "배당"]

        if any(keyword in entity for keyword in company_keywords):
            return "company"
        elif any(keyword in entity for keyword in tech_keywords):
            return "technology"
        elif any(keyword in entity for keyword in market_keywords):
            return "market"
        else:
            return "general"

    def _create_company_relationships(self, session):
        """회사 간 관계 생성"""
        relationships = [
            ("삼성전자", "SK하이닉스", "COMPETES_WITH"),
            ("네이버", "카카오", "COMPETES_WITH"),
            ("삼성전자", "반도체", "OPERATES_IN"),
            ("SK하이닉스", "반도체", "OPERATES_IN"),
            ("네이버", "AI", "DEVELOPS"),
            ("카카오", "AI", "DEVELOPS"),
        ]

        for entity1, entity2, relation_type in relationships:
            try:
                query = f"""
                MATCH (e1:Entity {{name: $entity1}})
                MATCH (e2:Entity {{name: $entity2}})
                MERGE (e1)-[:{relation_type}]->(e2)
                """
                session.run(query, {"entity1": entity1, "entity2": entity2})
            except Exception as e:
                print(f"관계 생성 실패 ({entity1}-{entity2}): {e}")

    def process_latest_news(self):
        """최신 수집된 뉴스를 Graph DB에 저장"""
        cache_dir = "/app/data/cache/playwright_news"

        if not os.path.exists(cache_dir):
            print(f"뉴스 캐시 디렉토리가 없습니다: {cache_dir}")
            return {"success": False, "error": "Cache directory not found"}

        # 최신 JSON 파일 찾기
        json_files = [f for f in os.listdir(cache_dir) if f.endswith(".json")]
        if not json_files:
            print("수집된 뉴스 파일이 없습니다")
            return {"success": False, "error": "No news files found"}

        # 가장 최신 파일 선택
        latest_file = max(
            json_files, key=lambda x: os.path.getctime(os.path.join(cache_dir, x))
        )
        file_path = os.path.join(cache_dir, latest_file)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 데이터 구조 확인
            if isinstance(data, list):
                news_items = data
            elif isinstance(data, dict) and "news_items" in data:
                news_items = data.get("news_items", [])
            else:
                print(f"예상하지 못한 데이터 구조: {type(data)}")
                return {"success": False, "error": "Unexpected data structure"}

            if not news_items:
                print("뉴스 데이터가 비어있습니다")
                return {"success": False, "error": "Empty news data"}

            print(f"최신 뉴스 파일 처리: {latest_file} ({len(news_items)}건)")
            success = self.create_news_graph(news_items)

            if success:
                # 통계 정보 수집
                stats = self.get_graph_stats()
                return {
                    "success": True,
                    "processed_file": latest_file,
                    "news_count": len(news_items),
                    "entities_created": stats.get("total_nodes", 0),
                    "relationships_created": stats.get("total_relationships", 0),
                }
            else:
                return {"success": False, "error": "Graph creation failed"}

        except json.JSONDecodeError as e:
            print(f"JSON 파싱 오류: {e}")
            return {"success": False, "error": f"JSON parsing error: {e}"}
        except Exception as e:
            print(f"뉴스 파일 처리 실패: {e}")
            return {"success": False, "error": f"Processing failed: {e}"}

    def get_graph_stats(self) -> Dict:
        """Graph DB 통계 조회"""
        try:
            driver = self.neo4j.get_driver()
            if not driver:
                return {"error": "Neo4j 연결 실패"}

            with driver.session() as session:
                # 노드 통계
                node_stats = session.run(
                    """
                    MATCH (n)
                    RETURN labels(n)[0] as label, count(n) as count
                    ORDER BY count DESC
                """
                ).data()

                # 관계 통계
                rel_stats = session.run(
                    """
                    MATCH ()-[r]->()
                    RETURN type(r) as relation_type, count(r) as count
                    ORDER BY count DESC
                """
                ).data()

                return {
                    "nodes": node_stats,
                    "relationships": rel_stats,
                    "total_nodes": sum(item["count"] for item in node_stats),
                    "total_relationships": sum(item["count"] for item in rel_stats),
                }

        except Exception as e:
            return {"error": f"통계 조회 실패: {e}"}


# 편의 함수들
def process_news_to_graph():
    """뉴스를 Graph DB로 처리하는 메인 함수"""
    pipeline = NewsToGraphPipeline()
    return pipeline.process_latest_news()


def get_graph_statistics():
    """Graph DB 통계 조회"""
    pipeline = NewsToGraphPipeline()
    return pipeline.get_graph_stats()
