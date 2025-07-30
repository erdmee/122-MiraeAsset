# app/services/enhanced_graph_rag.py

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import logging
from collections import defaultdict, Counter

from app.services.core.db import Neo4jConnection, ElasticsearchConnection
from app.services.external.hyperclova_client import HyperClovaXClient

logger = logging.getLogger(__name__)


class EnhancedGraphRAG:
    """실제 Neo4j 데이터를 활용한 고도화된 Graph RAG 시스템"""

    def __init__(self):
        try:
            self.neo4j_driver = Neo4jConnection.get_driver()
        except Exception as e:
            logger.warning(f"Neo4j 연결 실패: {e}")
            self.neo4j_driver = None

        self.es_client = ElasticsearchConnection.get_client()
        # Elasticsearch 연결 실패 시에도 계속 진행
        if self.es_client is None:
            logger.warning("Elasticsearch 연결 없이 제한된 기능으로 동작합니다")

        self.llm = HyperClovaXClient()

    def is_available(self) -> bool:
        """서비스 가용성 확인"""
        return self.neo4j_driver is not None or self.es_client is not None

    async def get_real_time_graph_context(
        self, query: str, user_context: Dict = None
    ) -> Dict[str, Any]:
        """실시간 Graph RAG 컨텍스트 생성"""

        if not self.is_available():
            return {
                "analysis": "현재 데이터베이스 연결이 불가능하여 제한된 응답만 제공 가능합니다.",
                "context": {},
                "entities": [],
                "relationships": [],
                "status": "limited",
            }

        # 1. 쿼리에서 엔티티 추출
        entities = await self._extract_entities_from_query(query)
        logger.info(f"추출된 엔티티: {entities}")

        # 2. Neo4j에서 실제 관계 데이터 수집
        graph_data = await self._collect_graph_data(entities)

        # 3. 최신 뉴스 데이터 수집 (지난 7일)
        recent_news = await self._get_recent_news(entities, days=7)

        # 4. 커뮤니티 검출 및 요약
        communities = await self._detect_communities(entities)

        # 5. 사용자 맞춤 필터링
        if user_context:
            graph_data = await self._personalize_context(graph_data, user_context)

        # 6. 컨텍스트 통합
        enhanced_context = {
            "entities": entities,
            "graph_relationships": graph_data,
            "recent_news": recent_news,
            "communities": communities,
            "analysis_timestamp": datetime.now().isoformat(),
            "data_freshness": {
                "news_count": len(recent_news),
                "relationship_count": len(graph_data.get("relationships", [])),
                "community_count": len(communities),
            },
        }

        logger.info(
            f"Graph RAG 컨텍스트 생성 완료: {enhanced_context['data_freshness']}"
        )
        return enhanced_context

    async def _extract_entities_from_query(self, query: str) -> List[str]:
        """LLM을 사용한 쿼리에서 엔티티 추출"""
        prompt = f"""
다음 투자 관련 질문에서 핵심 엔티티들을 추출해주세요.
기업명, 산업, 기술, 경제지표 등을 포함해야 합니다.

질문: {query}

JSON 형식으로 엔티티 리스트를 반환해주세요:
{{"entities": ["엔티티1", "엔티티2", ...]}}
"""

        try:
            # HyperCLOVA X는 동기 메서드 사용
            if hasattr(self.llm, "chat_completion"):
                messages = [{"role": "user", "content": prompt}]
                response = self.llm.chat_completion(
                    messages, max_tokens=200, temperature=0.3
                )
            else:
                # 더미 응답 생성 (API가 사용 불가능한 경우)
                dummy_content = '{"entities": ["삼성전자", "반도체", "AI", "투자"]}'
                response = self.llm._dummy_response(dummy_content)

            # 응답 내용 추출
            if hasattr(response, "get_content") and callable(response.get_content):
                response_text = response.get_content()
            elif isinstance(response, str):
                response_text = response
            else:
                response_text = str(response)

            # JSON 파싱
            if response_text and response_text.strip().startswith("{"):
                data = json.loads(response_text)
                return data.get("entities", [])
            else:
                # 더미 응답인 경우 기본 엔티티 반환
                return ["삼성전자", "반도체", "AI"]
        except Exception as e:
            logger.error(f"엔티티 추출 실패: {e}")
            return ["삼성전자", "반도체"]

    async def _collect_graph_data(self, entities: List[str]) -> Dict[str, Any]:
        """Neo4j에서 실제 관계 데이터 수집"""
        relationships = []
        entity_properties = {}

        with self.neo4j_driver.session() as session:
            # 엔티티 간 관계 검색
            for entity in entities:
                # 직접 관계 찾기
                result = session.run(
                    """
                    MATCH (a)-[r]->(b)
                    WHERE a.name CONTAINS $entity OR b.name CONTAINS $entity
                    RETURN a.name as source, type(r) as relation, b.name as target,
                           a.type as source_type, b.type as target_type
                    LIMIT 20
                """,
                    entity=entity,
                )

                for record in result:
                    relationships.append(
                        {
                            "source": record["source"],
                            "target": record["target"],
                            "relation": record["relation"],
                            "source_type": record["source_type"],
                            "target_type": record["target_type"],
                        }
                    )

                # 엔티티 속성 정보
                entity_result = session.run(
                    """
                    MATCH (n) WHERE n.name CONTAINS $entity
                    RETURN n.name as name, n.type as type,
                           n.sector as sector, n.market_cap as market_cap
                    LIMIT 5
                """,
                    entity=entity,
                )

                for record in entity_result:
                    entity_properties[record["name"]] = {
                        "type": record["type"],
                        "sector": record["sector"],
                        "market_cap": record["market_cap"],
                    }

        return {
            "relationships": relationships,
            "entities": entity_properties,
            "relationship_types": list(set(r["relation"] for r in relationships)),
        }

    async def _get_recent_news(self, entities: List[str], days: int = 7) -> List[Dict]:
        """최근 뉴스 데이터 수집"""
        recent_news = []
        cutoff_date = datetime.now() - timedelta(days=days)

        with self.neo4j_driver.session() as session:
            for entity in entities:
                result = session.run(
                    """
                    MATCH (c)-[:MENTIONS]-(news:News)
                    WHERE c.name CONTAINS $entity
                    AND datetime(news.crawled_at) >= datetime($cutoff_date)
                    RETURN news.title as title, news.summary as content,
                           news.published_at as date, news.source as press,
                           news.importance_score as importance
                    ORDER BY datetime(news.crawled_at) DESC
                    LIMIT 10
                """,
                    entity=entity,
                    cutoff_date=cutoff_date.isoformat(),
                )

                for record in result:
                    recent_news.append(
                        {
                            "title": record["title"],
                            "content": record["content"],
                            "date": record["date"],
                            "press": record["press"],
                            "importance": record["importance"],
                            "related_entity": entity,
                        }
                    )

        # 중요도순 정렬
        recent_news.sort(key=lambda x: x.get("importance", 0), reverse=True)
        return recent_news[:20]  # 상위 20개

    async def _detect_communities(self, entities: List[str]) -> List[Dict]:
        """커뮤니티 검출 및 요약"""
        communities = []

        with self.neo4j_driver.session() as session:
            # 간단한 커뮤니티 검출 (연결된 노드들 그룹화)
            for entity in entities:
                result = session.run(
                    """
                    MATCH (center)-[r]-(connected)
                    WHERE center.name CONTAINS $entity
                    RETURN center.name as center,
                           collect(distinct connected.name) as community_members,
                           collect(distinct type(r)) as relation_types
                    LIMIT 5
                """,
                    entity=entity,
                )

                for record in result:
                    community = {
                        "center": record["center"],
                        "members": record["community_members"][:10],  # 최대 10개
                        "relations": record["relation_types"],
                        "size": len(record["community_members"]),
                    }

                    # 커뮤니티 요약 생성
                    community["summary"] = await self._summarize_community(community)
                    communities.append(community)

        return communities

    async def _summarize_community(self, community: Dict) -> str:
        """커뮤니티 요약 생성"""
        prompt = f"""
다음 금융 엔티티 커뮤니티를 한 문장으로 요약해주세요:

중심 엔티티: {community['center']}
연결된 엔티티들: {', '.join(community['members'][:5])}
관계 유형들: {', '.join(community['relations'])}

예시: "삼성전자를 중심으로 한 반도체 생태계 커뮤니티"
"""

        try:
            if hasattr(self.llm, "chat"):
                return await self.llm.chat(prompt)
            else:
                return f"{community['center']}를 중심으로 한 {len(community['members'])}개 엔티티 커뮤니티"
        except:
            return f"{community['center']} 커뮤니티"

    async def _personalize_context(self, graph_data: Dict, user_context: Dict) -> Dict:
        """사용자 맞춤 컨텍스트 필터링"""
        user_stocks = user_context.get("holdings", [])
        user_interests = user_context.get("interests", [])

        # 사용자 보유 주식과 관심 분야 우선순위 적용
        prioritized_relationships = []

        for rel in graph_data.get("relationships", []):
            priority_score = 0

            # 보유 주식 관련 가중치
            if any(
                stock in rel["source"] or stock in rel["target"]
                for stock in user_stocks
            ):
                priority_score += 10

            # 관심 분야 관련 가중치
            if any(
                interest in rel["source"] or interest in rel["target"]
                for interest in user_interests
            ):
                priority_score += 5

            rel["priority_score"] = priority_score
            prioritized_relationships.append(rel)

        # 우선순위순 정렬
        prioritized_relationships.sort(key=lambda x: x["priority_score"], reverse=True)

        graph_data["relationships"] = prioritized_relationships[:50]  # 상위 50개
        return graph_data

    async def generate_graph_insight(
        self, context: Dict[str, Any], user_query: str
    ) -> str:
        """Graph RAG 기반 인사이트 생성"""

        # 커뮤니티 요약
        communities_summary = "\n".join(
            [
                f"- {comm['center']}: {comm['summary']} ({comm['size']}개 연결)"
                for comm in context.get("communities", [])[:5]
            ]
        )

        # 최신 뉴스 요약
        news_summary = "\n".join(
            [
                f"- {news['title']} (중요도: {news.get('importance', 0)})"
                for news in context.get("recent_news", [])[:5]
            ]
        )

        # 관계 네트워크 요약
        relationships = context.get("graph_relationships", {}).get("relationships", [])
        key_relationships = "\n".join(
            [
                f"- {rel['source']} → {rel['relation']} → {rel['target']}"
                for rel in relationships[:5]
            ]
        )

        prompt = f"""
당신은 금융 투자 전문가입니다. Graph RAG를 통해 수집된 실시간 데이터를 바탕으로 깊이 있는 투자 인사이트를 제공해주세요.

사용자 질문: {user_query}

=== Graph RAG 실시간 분석 결과 ===

📊 커뮤니티 분석:
{communities_summary}

📰 최신 뉴스 (지난 7일):
{news_summary}

🔗 핵심 관계 네트워크:
{key_relationships}

📈 데이터 신선도:
- 뉴스: {context.get('data_freshness', {}).get('news_count', 0)}건
- 관계: {context.get('data_freshness', {}).get('relationship_count', 0)}개
- 커뮤니티: {context.get('data_freshness', {}).get('community_count', 0)}개

위 Graph RAG 분석을 바탕으로:
1. 엔티티 간 관계에서 발견되는 숨겨진 패턴
2. 커뮤니티 중심성 기반 투자 기회
3. 최신 뉴스와 관계 네트워크의 교차 분석
4. 리스크 요인 및 기회 요인

이를 종합하여 실용적인 투자 인사이트를 제공해주세요.
"""

        try:
            if hasattr(self.llm, "chat"):
                return await self.llm.chat(prompt)
            else:
                return self.llm._dummy_response(prompt)
        except Exception as e:
            logger.error(f"인사이트 생성 실패: {e}")
            return "Graph RAG 기반 분석을 통해 시장의 연결 관계와 최신 동향을 종합한 결과, 현재 시장은 복합적인 요인들이 상호작용하고 있습니다."

    def create_market_narrative(self, financial_data: Dict) -> Dict[str, Any]:
        """시장 내러티브 생성 (하위 호환성을 위한 메서드)"""
        try:
            # 주요 엔티티 추출
            entities = []
            if financial_data.get("news"):
                for news in financial_data["news"][:10]:
                    if hasattr(news, "entities") and news.entities:
                        entities.extend(news.entities)

            # 엔티티 빈도 계산
            entity_counter = Counter(entities)
            top_entities = entity_counter.most_common(5)

            # 시장 요약 생성
            market_summary = {
                "top_entities": top_entities,
                "total_entities": len(entities),
                "unique_entities": len(set(entities)),
                "news_count": len(financial_data.get("news", [])),
                "analysis_timestamp": datetime.now().isoformat(),
            }

            # 기본 내러티브 생성
            narrative = self._generate_basic_narrative(financial_data, market_summary)

            return {
                "market_summary": market_summary,
                "narrative": narrative,
                "entities": list(set(entities)),
                "data_source": "enhanced_graph_rag",
            }

        except Exception as e:
            logger.error(f"시장 내러티브 생성 실패: {e}")
            return {
                "market_summary": {
                    "top_entities": [],
                    "total_entities": 0,
                    "unique_entities": 0,
                    "news_count": 0,
                    "analysis_timestamp": datetime.now().isoformat(),
                },
                "narrative": "시장 분석 중 오류가 발생했습니다.",
                "entities": [],
                "data_source": "enhanced_graph_rag",
            }

    def generate_insight_context(self, financial_data: Dict) -> str:
        """인사이트 컨텍스트 생성 (하위 호환성을 위한 메서드)"""
        try:
            # 뉴스 요약
            news_summary = ""
            if financial_data.get("news"):
                news_summary = (
                    f"최신 뉴스 {len(financial_data['news'])}건을 분석한 결과, "
                )
                top_news = financial_data["news"][:3]
                news_titles = [
                    news.title if hasattr(news, "title") else str(news)
                    for news in top_news
                ]
                news_summary += f"주요 이슈로는 {', '.join(news_titles[:2])} 등이 주목받고 있습니다."

            # 공시 정보 요약
            disclosure_summary = ""
            if financial_data.get("disclosures"):
                disclosure_summary = (
                    f"기업 공시 {len(financial_data['disclosures'])}건이 발표되었으며, "
                )
                if financial_data["disclosures"]:
                    disclosure_summary += "투자자들의 관심이 높아지고 있습니다."

            # 주식 데이터 요약
            stock_summary = ""
            if financial_data.get("stock_data"):
                positive_count = sum(
                    1
                    for stock in financial_data["stock_data"]
                    if hasattr(stock, "change_percent") and stock.change_percent > 0
                )
                total_count = len(financial_data["stock_data"])
                stock_summary = f"분석 대상 {total_count}개 종목 중 {positive_count}개가 상승세를 보이고 있습니다."

            # 전체 컨텍스트 조합
            context = f"""
Graph RAG 분석 컨텍스트:

시장 동향: {news_summary}
공시 현황: {disclosure_summary}
종목 현황: {stock_summary}

이러한 다양한 데이터 포인트들 간의 연관성을 분석하여 투자 인사이트를 도출합니다.
"""
            return context.strip()

        except Exception as e:
            logger.error(f"인사이트 컨텍스트 생성 실패: {e}")
            return "Graph RAG 기반 컨텍스트 분석을 통해 시장 상황을 종합적으로 검토하고 있습니다."

    def _generate_basic_narrative(
        self, financial_data: Dict, market_summary: Dict
    ) -> str:
        """기본 내러티브 생성"""
        try:
            news_count = market_summary.get("news_count", 0)
            entity_count = market_summary.get("unique_entities", 0)
            top_entities = market_summary.get("top_entities", [])

            narrative = f"현재 시장에서는 {news_count}건의 뉴스를 통해 {entity_count}개의 핵심 요소가 식별되었습니다."

            if top_entities:
                top_entity = top_entities[0]
                narrative += f" 특히 '{top_entity[0]}'이(가) {top_entity[1]}회 언급되며 가장 주목받는 키워드로 분석되었습니다."

            # 시장 상황 분석
            if financial_data.get("stock_data"):
                positive_stocks = [
                    s
                    for s in financial_data["stock_data"]
                    if hasattr(s, "change_percent") and s.change_percent > 0
                ]
                total_stocks = len(financial_data["stock_data"])

                if len(positive_stocks) > total_stocks * 0.6:
                    narrative += (
                        " 전반적으로 상승 모멘텀이 강화되고 있는 상황으로 판단됩니다."
                    )
                elif len(positive_stocks) < total_stocks * 0.4:
                    narrative += " 시장 전반에 조정 압력이 나타나고 있어 신중한 접근이 필요합니다."
                else:
                    narrative += " 혼조세 속에서 종목 선별의 중요성이 커지고 있습니다."

            return narrative

        except Exception as e:
            logger.error(f"기본 내러티브 생성 실패: {e}")
            return "시장 분석을 통해 현재 상황을 모니터링하고 있습니다."
