import openai
from typing import Dict, List, Optional
from datetime import datetime
import json
import sqlite3
from app.config import settings
from app.services.simple_graph_rag import SimpleGraphRAG
from app.services.enhanced_data_collector import EnhancedDataCollector


class PersonalizedInsightGenerator:
    """개인화된 AI 인사이트 생성기 (공시 정보 강화)"""

    def __init__(self):
        self.graph_rag = SimpleGraphRAG()
        self.data_collector = EnhancedDataCollector()
        self.client = (
            openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            if settings.OPENAI_API_KEY
            else None
        )
        if self.client:
            print(">> OpenAI API 클라이언트 초기화 완료")
        else:
            print(">> OpenAI API 키가 설정되지 않음. Mock 모드로 실행")

    def create_personalized_script_prompt(
        self, financial_data: Dict, user_profile: Dict
    ) -> str:
        """개인화된 스크립트 생성 프롬프트 (공시 정보 포함)"""
        graph_context = self.graph_rag.generate_insight_context(financial_data)
        portfolio = user_profile.get("portfolio", [])
        preferences = user_profile.get("preferences", {})

        # 포트폴리오 정보
        portfolio_info = ""
        portfolio_symbols = set()
        if portfolio:
            portfolio_info = "보유 종목:\n"
            for stock in portfolio:
                portfolio_info += (
                    f"- {stock[1]}({stock[0]}): {stock[2]}주 (평균 {stock[3]:,}원)\n"
                )
                portfolio_symbols.add(stock[0])

        # 사용자 맞춤 공시 정보 분석
        disclosure_analysis = self._analyze_disclosure_for_portfolio(
            financial_data.get("disclosures", []), portfolio_symbols
        )

        # 공시-뉴스 연관성 분석
        cross_analysis = self._analyze_disclosure_news_correlation(
            financial_data.get("disclosures", []), financial_data.get("news", [])
        )

        preferred_sectors = preferences.get("preferred_sectors", "").split(",")
        sector_info = (
            f"관심 섹터: {', '.join(preferred_sectors)}" if preferred_sectors else ""
        )
        investment_style = preferences.get("investment_style", "균형형")
        risk_level = preferences.get("risk_level", "중위험")

        prompt = f"""
당신은 개인 투자자를 위한 전문 AI 투자 어드바이저입니다. 일반인이 쉽게 접하지 못하는 기업 공시 정보와 실시간 뉴스를 종합하여 고급 투자 인사이트를 생성해주세요.

=== 시장 분석 정보 (Graph RAG) ===
{graph_context}

=== 투자자 프로필 ===
{portfolio_info}
{sector_info}
투자 스타일: {investment_style}
위험 수준: {risk_level}

=== 독점 공시 정보 분석 ===
{disclosure_analysis}

=== 공시-뉴스 연관성 분석 ===
{cross_analysis}

=== 전문가급 인사이트 작성 요구사항 ===

1. **차별화된 정보 활용**:
   - 일반 투자자가 놓치기 쉬운 공시 정보 해석
   - 공시와 뉴스의 숨겨진 연관성 발굴
   - 기업의 실제 경영 상황과 시장 반응 분석

2. **고급 분석 관점**:
   - 공시 정보로 본 기업의 미래 전략
   - 정량적 데이터와 정성적 뉴스의 교차 검증
   - 보유 종목의 숨겨진 리스크와 기회 요인

3. **개인화된 액션 아이템**:
   - 보유 종목별 구체적 모니터링 포인트
   - 공시 일정 기반 투자 타이밍 제안
   - 위험 관리를 위한 실용적 조치

4. **전문적 톤앤매너**:
   - 일반 뉴스에서 얻을 수 없는 통찰 제공
   - 데이터 기반의 논리적 근거 제시
   - 불확실성과 리스크에 대한 균형잡힌 시각

5. **출력 형식**:
   - 자연스러운 음성 스크립트 형태 (1000-1500자)
   - 전문적이지만 이해하기 쉬운 설명
   - 구체적 수치와 근거 포함

투자자가 "아, 이런 정보는 어디서도 들을 수 없었는데!"라고 느낄 수 있는 고품질 인사이트를 작성해주세요.
"""
        return prompt

    def _analyze_disclosure_for_portfolio(
        self, disclosures: List, portfolio_symbols: set
    ) -> str:
        """포트폴리오 종목 관련 공시 분석"""
        if not disclosures or not portfolio_symbols:
            return "현재 보유 종목과 관련된 최신 공시가 없습니다."

        relevant_disclosures = []

        # 종목 코드와 회사명 매핑 (간단한 예시)
        symbol_to_name = {
            "005930": "삼성전자",
            "000660": "SK하이닉스",
            "035420": "NAVER",
            "005380": "현대차",
            "051910": "LG화학",
        }

        portfolio_company_names = set()
        for symbol in portfolio_symbols:
            if symbol in symbol_to_name:
                portfolio_company_names.add(symbol_to_name[symbol])

        # 보유 종목 관련 공시 필터링
        for disclosure in disclosures:
            company_name = disclosure.company
            # 보유 종목과 관련된 공시 찾기
            for portfolio_company in portfolio_company_names:
                if portfolio_company in company_name:
                    relevant_disclosures.append(
                        {
                            "company": company_name,
                            "title": disclosure.title,
                            "date": disclosure.date,
                            "importance": disclosure.importance_score,
                        }
                    )

        if not relevant_disclosures:
            return "보유 종목들의 최근 공시는 대부분 정기 보고서로, 특별한 변화는 없어 보입니다. 안정적인 경영 상태를 유지하고 있는 것으로 판단됩니다."

        analysis = ">> 보유 종목 공시 분석:\n"
        for disclosure in relevant_disclosures[:5]:  # 상위 5개만
            analysis += f"- {disclosure['company']}: {disclosure['title']} ({disclosure['date']})\n"

            # 공시 유형별 분석 코멘트
            title_lower = disclosure["title"].lower()
            if "분기보고서" in title_lower:
                analysis += "  > 실적 발표 예정, 주가 변동성 예상\n"
            elif "사업보고서" in title_lower:
                analysis += "  > 연간 전략 및 사업 계획 공개, 장기 투자 관점에서 중요\n"
            elif "주주총회" in title_lower:
                analysis += "  > 배당 정책 및 경영진 변화 가능성 주목\n"
            elif "합병" in title_lower or "인수" in title_lower:
                analysis += "  > 기업 구조 변화, 고위험-고수익 상황\n"
            else:
                analysis += "  > 추가 모니터링 필요\n"

        return analysis

    def _analyze_disclosure_news_correlation(
        self, disclosures: List, news: List
    ) -> str:
        """공시와 뉴스의 연관성 분석"""
        if not disclosures or not news:
            return "공시와 뉴스 간 특별한 연관성이 발견되지 않았습니다."

        correlations = []

        # 공시와 뉴스에서 공통 키워드 찾기
        for disclosure in disclosures[:10]:  # 최근 10개 공시만
            disclosure_keywords = set(disclosure.title.split())
            disclosure_company = disclosure.company

            for news_item in news[:10]:  # 최근 10개 뉴스만
                news_title = news_item.title
                news_keywords = set(news_title.split())

                # 기업명 매칭
                if disclosure_company in news_title:
                    correlations.append(
                        {
                            "type": "기업명 매칭",
                            "company": disclosure_company,
                            "disclosure": disclosure.title,
                            "news": news_title,
                            "correlation_strength": "높음",
                        }
                    )

                # 키워드 매칭 (2개 이상 공통 키워드)
                common_keywords = disclosure_keywords.intersection(news_keywords)
                if len(common_keywords) >= 2:
                    correlations.append(
                        {
                            "type": "키워드 연관",
                            "company": disclosure_company,
                            "disclosure": disclosure.title,
                            "news": news_title,
                            "keywords": list(common_keywords),
                            "correlation_strength": "중간",
                        }
                    )

        if not correlations:
            return "현재 공시 정보와 뉴스 사이에 직접적인 연관성은 발견되지 않았으나, 이는 시장이 아직 공시 내용을 완전히 반영하지 못했을 가능성을 시사합니다."

        analysis = ">> 공시-뉴스 교차 분석:\n"
        for corr in correlations[:3]:  # 상위 3개만
            analysis += f"- {corr['company']}: 공시와 뉴스가 동시 부각\n"
            analysis += f"  공시: {corr['disclosure'][:50]}...\n"
            analysis += f"  뉴스: {corr['news'][:50]}...\n"
            analysis += f"  > 시장 관심도가 높은 상황, 주가 변동성 확대 가능성\n"

        return analysis

    def _filter_personalized_news(
        self, financial_data: Dict, user_profile: Dict
    ) -> List[Dict]:
        """개인화된 뉴스 필터링 (공시 연관성 포함)"""
        news_items = financial_data.get("news", [])
        disclosures = financial_data.get("disclosures", [])

        # 공시와 연관된 뉴스에 가중치 부여
        enhanced_news = []

        for news in news_items:
            relevance_score = news.importance_score

            # 공시와 연관성 체크
            for disclosure in disclosures:
                if disclosure.company in news.title:
                    relevance_score += 1.0  # 공시 연관 보너스

            enhanced_news.append(
                {
                    "title": news.title,
                    "summary": news.summary,
                    "entities": news.entities,
                    "importance_score": news.importance_score,
                    "relevance_score": relevance_score,
                    "has_disclosure_link": any(
                        d.company in news.title for d in disclosures
                    ),
                }
            )

        # 관련성 점수 순으로 정렬
        enhanced_news.sort(key=lambda x: x["relevance_score"], reverse=True)

        return enhanced_news[:5]

    def generate_personalized_insight(
        self, financial_data: Dict, user_id: str
    ) -> Optional[Dict]:
        """개인화된 인사이트 생성 (공시 정보 강화)"""
        print(f">> 사용자 {user_id}를 위한 고급 인사이트 생성 시작")
        user_profile = self.data_collector.get_personalized_data(user_id)

        if not self.client:
            print(">> Mock 고급 인사이트 생성 중...")
            return self.generate_mock_personalized_insight(financial_data, user_profile)

        try:
            prompt = self.create_personalized_script_prompt(
                financial_data, user_profile
            )
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 기업 공시 정보와 시장 뉴스를 종합 분석하는 전문 투자 어드바이저입니다. 일반인이 접하기 어려운 정보를 바탕으로 고급 투자 인사이트를 제공합니다.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=2000,  # 더 긴 인사이트를 위해 토큰 증가
                temperature=0.7,
            )
            script_content = response.choices[0].message.content.strip()

            return {
                "script": script_content,
                "user_id": user_id,
                "analysis_method": "Enhanced OpenAI + Graph RAG + DART Disclosures",
                "portfolio_analysis": self._analyze_portfolio_performance(
                    user_profile, financial_data
                ),
                "personalized_news": self._filter_personalized_news(
                    financial_data, user_profile
                ),
                "disclosure_insights": self._analyze_disclosure_for_portfolio(
                    financial_data.get("disclosures", []),
                    set(holding[0] for holding in user_profile.get("portfolio", [])),
                ),
                "graph_analysis": self.graph_rag.create_market_narrative(
                    financial_data
                ),
                "token_usage": (
                    response.usage.total_tokens if hasattr(response, "usage") else 0
                ),
                "model_used": settings.OPENAI_MODEL,
                "data_sources": {
                    "news_count": len(financial_data.get("news", [])),
                    "disclosure_count": len(financial_data.get("disclosures", [])),
                    "stock_count": len(financial_data.get("stock_data", [])),
                },
            }
        except Exception as e:
            print(f">> 고급 인사이트 생성 실패: {e}")
            return self.generate_mock_personalized_insight(financial_data, user_profile)

    def _analyze_portfolio_performance(
        self, user_profile: Dict, financial_data: Dict
    ) -> Dict:
        """포트폴리오 성과 분석 (실제 데이터만 사용)"""
        portfolio = user_profile.get("portfolio", [])
        if not portfolio:
            return {
                "total_value": 0,
                "total_cost": 0,
                "total_return": 0,
                "total_return_percent": 0.0,
                "holdings_count": 0,
                "best_performer": None,
                "worst_performer": None,
                "error": "포트폴리오 데이터가 없습니다.",
            }

        # 주식 데이터를 딕셔너리로 변환하여 빠른 검색 가능
        stock_data_map = {}
        for stock in financial_data.get("stock_data", []):
            stock_data_map[stock.symbol] = stock

        total_value = 0
        total_cost = 0
        holdings_analysis = []
        missing_data_count = 0

        print(f">> 포트폴리오 분석: {len(portfolio)}개 보유 종목")

        for holding in portfolio:
            # 튜플 인덱스로 데이터에 접근
            symbol, company_name, shares, avg_price = (
                holding[0],
                holding[1],
                holding[2],
                holding[3],
            )

            print(
                f">> 분석 중: {company_name}({symbol}) - {shares}주, 평균 {avg_price:,}원"
            )

            # 현재 주가 찾기
            current_price = None
            data_source = "실제 데이터 없음"

            if symbol in stock_data_map:
                stock_info = stock_data_map[symbol]
                # FIX: 0원이거나 유효하지 않은 데이터 체크
                if stock_info.price > 0:
                    current_price = stock_info.price
                    data_source = "실시간 데이터"
                    print(f"   >> 실제 현재가: {current_price:,}원")
                else:
                    print(
                        f"   >> 수집된 데이터가 유효하지 않음 (가격: {stock_info.price})"
                    )
                    missing_data_count += 1
            else:
                print(f"   >> 실시간 데이터 없음")
                missing_data_count += 1

            # 실제 데이터가 없는 경우 분석에서 제외
            if current_price is None:
                holdings_analysis.append(
                    {
                        "symbol": symbol,
                        "company_name": company_name,
                        "shares": shares,
                        "avg_price": avg_price,
                        "current_price": None,
                        "cost": avg_price * shares,
                        "value": None,
                        "return": None,
                        "return_percent": None,
                        "data_source": data_source,
                        "error": "실시간 데이터 없음",
                    }
                )
                continue

            # 개별 종목 성과 계산 (실제 데이터가 있는 경우만)
            holding_cost = avg_price * shares
            holding_value = current_price * shares
            holding_return = holding_value - holding_cost
            holding_return_percent = (
                (holding_return / holding_cost) * 100 if holding_cost > 0 else 0
            )

            holdings_analysis.append(
                {
                    "symbol": symbol,
                    "company_name": company_name,
                    "shares": shares,
                    "avg_price": avg_price,
                    "current_price": current_price,
                    "cost": holding_cost,
                    "value": holding_value,
                    "return": holding_return,
                    "return_percent": holding_return_percent,
                    "data_source": data_source,
                }
            )

            total_cost += holding_cost
            total_value += holding_value

            print(f"   >> 수익: {holding_return:+,}원 ({holding_return_percent:+.2f}%)")

        # 전체 수익률 계산
        total_return = total_value - total_cost
        total_return_percent = (
            (total_return / total_cost) * 100 if total_cost > 0 else 0
        )

        # 실제 데이터가 있는 종목들만으로 최고/최저 수익 종목 찾기
        valid_holdings = [
            h for h in holdings_analysis if h.get("return_percent") is not None
        ]
        best_performer = (
            max(valid_holdings, key=lambda x: x["return_percent"])
            if valid_holdings
            else None
        )
        worst_performer = (
            min(valid_holdings, key=lambda x: x["return_percent"])
            if valid_holdings
            else None
        )

        # 데이터 품질 체크
        data_quality_warning = None
        if missing_data_count > 0:
            data_quality_warning = f"{missing_data_count}개 종목의 실시간 데이터를 가져올 수 없어서 분석에서 제외되었습니다."

        result = {
            "total_value": total_value,
            "total_cost": total_cost,
            "total_return": total_return,
            "total_return_percent": total_return_percent,
            "holdings_count": len(portfolio),
            "analyzed_holdings_count": len(valid_holdings),
            "missing_data_count": missing_data_count,
            "best_performer": best_performer,
            "worst_performer": worst_performer,
            "holdings_detail": holdings_analysis,
            "data_quality_warning": data_quality_warning,
        }

        print(f">> 포트폴리오 분석 결과:")
        print(f"   총 보유 종목: {len(portfolio)}개")
        print(f"   분석 가능 종목: {len(valid_holdings)}개")
        if missing_data_count > 0:
            print(f"   >> 데이터 없는 종목: {missing_data_count}개")
        if valid_holdings:
            print(f"   투자금: {total_cost:,}원")
            print(f"   평가액: {total_value:,}원")
            print(f"   수익: {total_return:+,}원 ({total_return_percent:+.2f}%)")
        else:
            print(
                f"   >> 모든 종목의 실시간 데이터가 없어서 수익률을 계산할 수 없습니다."
            )

        return result

    def _filter_personalized_news(
        self, financial_data: Dict, user_profile: Dict
    ) -> List[Dict]:
        """개인화된 뉴스 필터링"""
        # (기존 로직과 유사하게 유지, 필요시 수정)
        return financial_data.get("news", [])[:5]

    def _find_investment_opportunities(
        self, user_profile: Dict, financial_data: Dict
    ) -> List[Dict]:
        """개인화된 투자 기회 발굴"""
        # (기존 로직과 유사하게 유지, 필요시 수정)
        return []

    def generate_mock_personalized_insight(
        self, financial_data: Dict, user_profile: Dict
    ) -> Dict:
        """Mock 개인화 인사이트 생성 (오류 방지 강화)"""
        portfolio_analysis = self._analyze_portfolio_performance(
            user_profile, financial_data
        )
        graph_analysis = self.graph_rag.create_market_narrative(financial_data)

        # FIX: IndexError 방지를 위한 방어 코드
        top_entity_info = "분석된 핵심 엔티티가 없습니다."
        if graph_analysis and graph_analysis.get("market_summary", {}).get(
            "top_entities"
        ):
            top_entity = graph_analysis["market_summary"]["top_entities"][0]
            top_entity_info = f"{top_entity[0]}이(가) 가장 주목받는 핵심 요소로 분석되었습니다 (중요도: {top_entity[1]}점)."

        script = f"""
안녕하세요, Mock 데이터 기반 맞춤형 투자 인사이트입니다.
포트폴리오 총 수익률은 {portfolio_analysis.get('total_return_percent', 0):.2f}% 입니다.
오늘 시장 전반적으로는 {top_entity_info}
투자에 도움이 되시길 바랍니다.
"""
        return {
            "script": script.strip(),
            "user_id": "mock_user",
            "analysis_method": "Mock Personalized + Graph RAG",
            "portfolio_analysis": portfolio_analysis,
            "personalized_news": [],
            "investment_opportunities": [],
            "graph_analysis": graph_analysis,
        }

    def save_user_portfolio(self, user_id: str, portfolio_data: List[Dict]):
        """사용자 포트폴리오 저장"""
        conn = sqlite3.connect(self.data_collector.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_portfolios WHERE user_id = ?", (user_id,))
        cursor.executemany(
            "INSERT INTO user_portfolios (user_id, symbol, company_name, shares, avg_price, sector) VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    user_id,
                    h["symbol"],
                    h["company_name"],
                    h["shares"],
                    h["avg_price"],
                    h.get("sector"),
                )
                for h in portfolio_data
            ],
        )
        conn.commit()
        conn.close()

    def save_user_preferences(self, user_id: str, preferences: Dict):
        """사용자 투자 선호도 저장"""
        conn = sqlite3.connect(self.data_collector.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO user_preferences (user_id, preferred_sectors, risk_level, investment_style, news_keywords) VALUES (?, ?, ?, ?, ?)",
            (
                user_id,
                ",".join(preferences.get("preferred_sectors", [])),
                preferences.get("risk_level", "중위험"),
                preferences.get("investment_style", "균형형"),
                ",".join(preferences.get("news_keywords", [])),
            ),
        )
        conn.commit()
        conn.close()

    def generate_comprehensive_insight(
        self, user_id: str, refresh_data: bool = False
    ) -> Optional[Dict]:
        """종합적인 개인화 인사이트 생성"""
        print(f">> 사용자 {user_id}를 위한 종합 인사이트 생성 시작")
        financial_data = self.data_collector.collect_all_data(user_id, refresh_data)
        insight_result = self.generate_personalized_insight(financial_data, user_id)

        if insight_result:
            insight_result.update(
                {
                    "script_length": len(insight_result.get("script", "")),
                    "estimated_reading_time": f"{len(insight_result.get('script', '')) // 200}분",
                }
            )
            print(
                f"개인화 인사이트 생성 완료 (길이: {insight_result['script_length']}자)"
            )

        return insight_result
