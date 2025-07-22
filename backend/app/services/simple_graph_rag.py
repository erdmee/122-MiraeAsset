# app/services/simple_graph_rag.py (개선된 버전)

from typing import Dict, List, Tuple, Set
from collections import defaultdict, Counter
from datetime import datetime
import json


class SimpleGraphRAG:
    """간단하고 실용적인 Graph RAG 시스템 (Playwright 데이터 강화)"""

    def __init__(self):
        # 미리 정의된 엔티티 관계 그래프 (확장됨)
        self.entity_relations = {
            # 기업 관계
            "삼성전자": ["SK하이닉스", "반도체", "메모리", "AI", "TSMC"],
            "SK하이닉스": ["삼성전자", "반도체", "메모리", "AI", "NVIDIA"],
            "LG화학": ["배터리", "전기차", "2차전지", "현대차", "SK이노베이션"],
            "현대차": ["전기차", "자동차", "배터리", "LG화학", "기아"],
            "네이버": ["IT", "플랫폼", "카카오", "AI", "클라우드"],
            "카카오": ["IT", "플랫폼", "네이버", "핀테크", "게임"],
            # 해외 기업
            "NVIDIA": ["AI", "반도체", "SK하이닉스", "데이터센터", "GPU"],
            "TSMC": ["반도체", "삼성전자", "AI", "파운드리", "칩"],
            # 암호화폐 관련 (Playwright로 수집된 새로운 엔티티들)
            "비트코인": [
                "암호화폐",
                "블록체인",
                "스테이블코인",
                "디지털자산",
                "퇴직연금",
            ],
            "스테이블코인": ["비트코인", "암호화폐", "블록체인", "USDT", "USDC"],
            "암호화폐": ["비트코인", "스테이블코인", "블록체인", "리플", "이더리움"],
            "블록체인": ["비트코인", "암호화폐", "스테이블코인", "NFT", "DeFi"],
            # AI 관련 (확장됨)
            "AI": [
                "반도체",
                "NVIDIA",
                "데이터센터",
                "클라우드",
                "빅테크",
                "인공지능",
                "머신러닝",
            ],
            "인공지능": ["AI", "머신러닝", "딥러닝", "반도체", "데이터센터"],
            # 섹터 관계 (확장됨)
            "반도체": ["AI", "메모리", "삼성전자", "SK하이닉스", "TSMC", "NVIDIA"],
            "전기차": ["배터리", "자동차", "2차전지", "현대차", "LG화학"],
            "배터리": ["전기차", "2차전지", "LG화학", "SK이노베이션", "리튬"],
            "IT": ["AI", "플랫폼", "클라우드", "소프트웨어", "빅테크"],
            "금융": ["은행", "보험", "핀테크", "기준금리", "금리", "투자"],
            # 경제 지표
            "기준금리": ["금융", "은행", "부동산", "대출", "통화정책"],
            "환율": ["수출", "무역", "달러", "원화", "경제"],
            "코스피": ["주식", "증시", "외국인", "기관", "개인"],
        }

        # 엔티티 중요도 가중치 (업데이트됨)
        self.entity_weights = {
            # 기존 기업들
            "삼성전자": 5,
            "SK하이닉스": 4,
            "NVIDIA": 5,
            "TSMC": 4,
            "네이버": 3,
            "카카오": 3,
            "현대차": 3,
            "LG화학": 3,
            # 새로 추가된 암호화폐 관련
            "비트코인": 5,
            "스테이블코인": 3,
            "암호화폐": 4,
            "블록체인": 3,
            # AI 관련
            "AI": 5,
            "인공지능": 4,
            # 섹터
            "반도체": 4,
            "전기차": 4,
            "배터리": 3,
            "IT": 3,
            # 금융 지표
            "기준금리": 5,
            "환율": 4,
            "코스피": 4,
            "인플레이션": 4,
        }

    def extract_entities_from_data(self, financial_data: Dict) -> List[str]:
        """금융 데이터에서 엔티티 추출 (Playwright 데이터 강화)"""
        entities = set()

        # 뉴스에서 엔티티 추출 (Playwright로 수집된 풍부한 데이터)
        for news in financial_data.get("news", []):
            # 기존 엔티티 추가
            entities.update(news.entities)

            # 제목과 본문에서 추가 엔티티 추출 (Playwright 장점 활용)
            if hasattr(news, "summary") and news.summary:
                # 본문 내용에서 추가 엔티티 찾기
                additional_entities = self._extract_entities_from_text(
                    news.title + " " + news.summary
                )
                entities.update(additional_entities)

        # 공시에서 기업명 추출
        for disclosure in financial_data.get("disclosures", []):
            company = disclosure.company
            if company in self.entity_relations:
                entities.add(company)

            # 공시 제목에서 추가 엔티티 추출
            title_entities = self._extract_entities_from_text(disclosure.title)
            entities.update(title_entities)

        # 주식 데이터에서 기업명 추가
        for stock in financial_data.get("stock_data", []):
            if stock.company_name in self.entity_relations:
                entities.add(stock.company_name)

        return list(entities)

    def _extract_entities_from_text(self, text: str) -> Set[str]:
        """텍스트에서 엔티티 추출 (Playwright 본문 활용)"""
        entities = set()

        # 모든 알려진 엔티티 검사
        for entity in self.entity_relations.keys():
            if entity in text:
                entities.add(entity)

        # 가중치가 있는 엔티티도 검사
        for entity in self.entity_weights.keys():
            if entity in text:
                entities.add(entity)

        return entities

    def calculate_entity_importance(
        self, entities: List[str], news_data: List
    ) -> Dict[str, float]:
        """엔티티 중요도 계산 (Playwright 데이터 강화)"""
        importance_scores = {}

        # 뉴스 언급 빈도 계산 (본문 내용 포함)
        entity_mentions = Counter()
        content_mentions = Counter()  # 본문에서의 언급

        for news in news_data:
            # 제목에서의 언급 (기존)
            for entity in news.entities:
                entity_mentions[entity] += 1

            # 본문에서의 언급 (Playwright 장점)
            if hasattr(news, "summary") and news.summary:
                for entity in entities:
                    if entity in news.summary:
                        content_mentions[entity] += 1

        for entity in entities:
            # 기본 중요도
            base_weight = self.entity_weights.get(entity, 1.0)

            # 제목 언급 빈도 보너스 (높은 가중치)
            title_bonus = entity_mentions.get(entity, 0) * 0.8

            # 본문 언급 빈도 보너스 (중간 가중치)
            content_bonus = content_mentions.get(entity, 0) * 0.3

            # 관계 개수 보너스
            relation_count = len(self.entity_relations.get(entity, []))
            relation_bonus = min(relation_count * 0.1, 1.0)

            # 최종 중요도 계산
            total_score = base_weight + title_bonus + content_bonus + relation_bonus
            importance_scores[entity] = round(total_score, 2)

        return importance_scores

    def analyze_entity_clusters(self, entities: List[str]) -> Dict[str, List[str]]:
        """엔티티 클러스터 분석 (업데이트된 섹터)"""
        clusters = defaultdict(list)

        # 확장된 섹터별 분류
        sector_mapping = {
            "반도체": ["삼성전자", "SK하이닉스", "TSMC", "NVIDIA", "반도체", "메모리"],
            "전기차": ["현대차", "LG화학", "배터리", "2차전지", "전기차"],
            "IT": ["네이버", "카카오", "AI", "플랫폼", "인공지능", "클라우드"],
            "암호화폐": [
                "비트코인",
                "스테이블코인",
                "암호화폐",
                "블록체인",
            ],  # 새로 추가
            "금융": ["기준금리", "환율", "코스피", "코스닥", "투자", "금융"],
            "에너지": ["유가", "화학", "원자재"],
        }

        for entity in entities:
            assigned = False
            for sector, sector_entities in sector_mapping.items():
                if entity in sector_entities:
                    clusters[sector].append(entity)
                    assigned = True
                    break

            if not assigned:
                clusters["기타"].append(entity)

        return dict(clusters)

    def create_market_narrative(self, financial_data: Dict) -> Dict:
        """시장 내러티브 생성 (Playwright 데이터 활용)"""
        entities = self.extract_entities_from_data(financial_data)

        print(f">>> Graph RAG: {len(entities)}개 엔티티 추출")

        # 엔티티 중요도 분석 (본문 데이터 활용)
        importance_scores = self.calculate_entity_importance(
            entities, financial_data.get("news", [])
        )

        # 클러스터 분석 (업데이트된 섹터)
        clusters = self.analyze_entity_clusters(entities)

        # 영향 분석
        impact_analysis = self.generate_impact_analysis(entities)

        # 상위 엔티티 선별
        top_entities = sorted(
            importance_scores.items(), key=lambda x: x[1], reverse=True
        )[:10]

        # 핵심 테마 추출 (암호화폐 테마 추가)
        main_themes = []
        for cluster_name, cluster_entities in clusters.items():
            if len(cluster_entities) >= 1:  # 1개 이상 엔티티가 있는 클러스터
                theme_importance = sum(
                    importance_scores.get(e, 0) for e in cluster_entities
                )
                main_themes.append(
                    {
                        "theme": cluster_name,
                        "entities": cluster_entities,
                        "importance": theme_importance,
                        "entity_count": len(cluster_entities),
                    }
                )

        main_themes.sort(key=lambda x: x["importance"], reverse=True)

        # 시장 동향 요약
        market_summary = {
            "total_entities": len(entities),
            "top_entities": top_entities[:8],
            "main_themes": main_themes[:5],  # 상위 5개 테마
            "impact_chains": impact_analysis["impact_chains"][:3],
            "market_indices": financial_data.get("market", []),
            "news_coverage": {
                "total_news": len(financial_data.get("news", [])),
                "crypto_news": len(
                    [
                        n
                        for n in financial_data.get("news", [])
                        if any(
                            crypto in n.entities
                            for crypto in ["비트코인", "암호화폐", "스테이블코인"]
                        )
                    ]
                ),
                "ai_news": len(
                    [
                        n
                        for n in financial_data.get("news", [])
                        if any(ai in n.entities for ai in ["AI", "인공지능"])
                    ]
                ),
            },
        }

        print(f">>> Graph RAG: 상위 테마 {len(main_themes)}개 생성")
        for theme in main_themes[:3]:
            print(
                f"  - {theme['theme']}: {theme['entity_count']}개 엔티티 (중요도: {theme['importance']:.1f})"
            )

        return {
            "entities": entities,
            "importance_scores": importance_scores,
            "clusters": clusters,
            "impact_analysis": impact_analysis,
            "market_summary": market_summary,
            "analysis_timestamp": datetime.now().isoformat(),
            "data_quality": {
                "has_content": any(
                    hasattr(n, "summary") and n.summary
                    for n in financial_data.get("news", [])
                ),
                "entity_coverage": len(entities)
                / max(len(financial_data.get("news", [])), 1),
            },
        }

    def generate_impact_analysis(self, entities: List[str]) -> Dict:
        """영향 분석 생성 (기존 로직 유지)"""
        impact_chains = []

        for entity in entities:
            if entity in self.entity_relations:
                related = self.entity_relations[entity][:3]
                positive_impact = []
                negative_impact = []

                for related_entity in related:
                    if related_entity in entities:
                        # 긍정적/부정적 영향 분류 (간단한 규칙)
                        if entity in ["삼성전자", "SK하이닉스"] and related_entity in [
                            "AI",
                            "반도체",
                        ]:
                            positive_impact.append(related_entity)
                        elif entity == "비트코인" and related_entity in [
                            "암호화폐",
                            "블록체인",
                        ]:
                            positive_impact.append(related_entity)
                        elif entity == "기준금리" and related_entity == "금융":
                            negative_impact.append(related_entity)
                        else:
                            positive_impact.append(related_entity)

                if positive_impact or negative_impact:
                    impact_chains.append(
                        {
                            "source": entity,
                            "positive_impact": positive_impact,
                            "negative_impact": negative_impact,
                        }
                    )

        return {
            "impact_chains": impact_chains,
            "total_entities": len(entities),
            "connected_entities": len(
                [e for e in entities if e in self.entity_relations]
            ),
        }

    def generate_insight_context(self, financial_data: Dict) -> str:
        """인사이트 생성을 위한 컨텍스트 생성 (Playwright 데이터 활용)"""
        narrative = self.create_market_narrative(financial_data)

        context = f"""
=== 금융 시장 Graph RAG 분석 결과 (Playwright 강화) ===

📊 데이터 품질:
- 총 뉴스: {narrative['market_summary']['news_coverage']['total_news']}건
- 암호화폐 뉴스: {narrative['market_summary']['news_coverage']['crypto_news']}건
- AI 관련 뉴스: {narrative['market_summary']['news_coverage']['ai_news']}건
- 본문 데이터 활용: {'예' if narrative['data_quality']['has_content'] else '아니오'}

🔥 핵심 엔티티 (중요도순):
"""

        # 상위 엔티티
        for i, (entity, score) in enumerate(
            narrative["market_summary"]["top_entities"][:5], 1
        ):
            context += f"- {entity}: {score}점\n"

        context += f"""
🎯 주요 테마:
"""

        # 주요 테마
        for i, theme in enumerate(narrative["market_summary"]["main_themes"][:3], 1):
            entities_str = ", ".join(theme["entities"])
            context += f"- {theme['theme']}: {entities_str} (중요도: {theme['importance']:.1f})\n"

        context += f"""
⚡ 영향 관계:
"""

        # 영향 체인
        for chain in narrative["market_summary"]["impact_chains"][:3]:
            source = chain["source"]
            positive = (
                ", ".join(chain["positive_impact"])
                if chain["positive_impact"]
                else "없음"
            )
            context += f"- {source} → 긍정적 영향: {positive}\n"

        context += f"""
📰 주요 뉴스 (상위 3개):
"""

        # 중요도 높은 뉴스 (본문 내용 포함)
        sorted_news = sorted(
            financial_data.get("news", []),
            key=lambda x: x.importance_score,
            reverse=True,
        )
        for i, news in enumerate(sorted_news[:3], 1):
            context += f"{i}. {news.title} (중요도: {news.importance_score})\n"
            context += f"   엔티티: {', '.join(news.entities)}\n"
            if hasattr(news, "summary") and news.summary:
                context += f"   내용: {news.summary[:150]}...\n"

        return context
