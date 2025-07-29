from typing import Dict, List, Optional
from datetime import datetime
import json
import sqlite3
from app.config import settings
from app.services.simple_graph_rag import SimpleGraphRAG
from app.services.enhanced_data_collector import EnhancedDataCollector
from app.services.hyperclova_client import UnifiedLLMClient


class PersonalizedInsightGenerator:
    """개인화된 AI 인사이트 생성기 (HyperCLOVA X 지원)"""

    def __init__(self):
        self.graph_rag = SimpleGraphRAG()
        self.data_collector = EnhancedDataCollector()
        self.llm_client = UnifiedLLMClient()

        if self.llm_client.is_available():
            provider = self.llm_client.get_current_provider()
            print(f">> AI 인사이트 생성기 초기화 완료 (사용: {provider})")
        else:
            print(">> 사용 가능한 LLM API가 없음. Mock 모드로 실행")

    def create_personalized_script_prompt(
        self, financial_data: Dict, user_profile: Dict
    ) -> str:
        """개인화된 스크립트 생성 프롬프트 (한국어 최적화)"""
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

        # 실제 뉴스 데이터 포함
        recent_news = ""
        if financial_data.get("news"):
            recent_news = "최신 뉴스 헤드라인:\n"
            for i, news in enumerate(financial_data.get("news", [])[:5], 1):
                recent_news += f"{i}. {news.title}\n"

        # 실제 주식 데이터 포함
        stock_performance = ""
        if financial_data.get("stock_data"):
            stock_performance = "주요 종목 현황:\n"
            for stock in financial_data.get("stock_data", [])[:3]:
                change_sign = "+" if stock.change_percent > 0 else ""
                stock_performance += f"- {stock.symbol}: {stock.price:,}원 ({change_sign}{stock.change_percent:.2f}%)\n"

        # HyperCLOVA X에 최적화된 구체적이고 전문적인 한국어 프롬프트
        prompt = f"""
당신은 한국 금융시장의 최고 전문가이며, 개인 투자자를 위한 프리미엄 투자 어드바이저입니다.
실제 시장 데이터와 공시 정보를 바탕으로 깊이 있고 실용적인 투자 인사이트를 제공해주세요.

=== 현재 시장 상황 ===
{stock_performance}

=== 최신 시장 뉴스 ===
{recent_news}

=== 시장 분석 정보 (Graph RAG) ===
{graph_context}

=== 투자자 프로필 ===
{portfolio_info}
{sector_info}
투자 스타일: {investment_style}
위험 수준: {risk_level}

=== 공시 정보 분석 ===
{disclosure_analysis}

=== 공시-뉴스 연관성 분석 ===
{cross_analysis}

=== 고품질 투자 인사이트 작성 요구사항 ===

**톤 앤 매너:**
- 전문적이면서도 친근한 투자 전문가의 어조
- 확신에 찬 분석이지만 리스크에 대한 균형잡힌 시각 유지
- 일반적인 뉴스가 아닌 '인사이더 정보'를 제공하는 느낌

**내용 구성:**
1. **오프닝**: 현재 시장 상황에 대한 핵심 진단 (30초 분량)
2. **포트폴리오 분석**: 보유 종목별 구체적 분석과 전망 (60초 분량)
3. **시장 기회**: 놓치기 쉬운 투자 기회나 주의점 제시 (45초 분량)
4. **액션 아이템**: 구체적이고 실행 가능한 투자 조치 제안 (30초 분량)
5. **마무리**: 다음 모니터링 포인트 안내 (15초 분량)

**반드시 포함해야 할 요소:**
- 구체적인 수치와 데이터 (주가, 수익률, 거래량 등)
- 시장 상황에 대한 명확한 판단 ("강세", "약세", "횡보" 등)
- 보유 종목에 대한 개별적 분석
- 단기(1-3개월)와 중기(6개월-1년) 전망 구분
- 리스크 요인과 대응 방안

**절대 하지 말아야 할 것:**
- 너무 일반적이거나 뻔한 내용
- 애매모호한 표현 ("좋을 것 같다", "나쁘지 않다" 등)
- 단순한 뉴스 요약
- 책임 회피성 문구 과다 사용

**목표 분량**: 1200-1500자 (약 3-4분 읽기 분량)
**스타일**: 프리미엄 자산관리사의 개인 브리핑 느낌

현재 시장 데이터와 투자자의 포트폴리오를 바탕으로, 투자자가 "이런 분석은 어디서도 들을 수 없었다"고 감탄할 만한 고품질 인사이트를 작성해주세요.
"""
        return prompt

    def _analyze_disclosure_for_portfolio(
        self, disclosures: List, portfolio_symbols: set
    ) -> str:
        """포트폴리오 종목 관련 공시 분석"""
        if not disclosures or not portfolio_symbols:
            return "현재 보유 종목과 관련된 최신 공시가 없습니다."

        relevant_disclosures = []

        # 종목 코드와 회사명 매핑
        symbol_to_name = {
            "005930": "삼성전자",
            "000660": "SK하이닉스",
            "035420": "NAVER",
            "005380": "현대차",
            "051910": "LG화학",
            "035720": "카카오",
            "005490": "POSCO홀딩스",
            "207940": "삼성바이오로직스",
            "068270": "셀트리온",
        }

        portfolio_company_names = set()
        for symbol in portfolio_symbols:
            if symbol in symbol_to_name:
                portfolio_company_names.add(symbol_to_name[symbol])

        # 보유 종목 관련 공시 필터링
        for disclosure in disclosures:
            company_name = disclosure.company
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
        for disclosure in relevant_disclosures[:5]:
            analysis += f"- {disclosure['company']}: {disclosure['title']} ({disclosure['date']})\n"

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

        for disclosure in disclosures[:10]:
            disclosure_keywords = set(disclosure.title.split())
            disclosure_company = disclosure.company

            for news_item in news[:10]:
                news_title = news_item.title
                news_keywords = set(news_title.split())

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
        for corr in correlations[:3]:
            analysis += f"- {corr['company']}: 공시와 뉴스가 동시 부각\n"
            analysis += f"  공시: {corr['disclosure'][:50]}...\n"
            analysis += f"  뉴스: {corr['news'][:50]}...\n"
            analysis += f"  > 시장 관심도가 높은 상황, 주가 변동성 확대 가능성\n"

        return analysis

    def generate_personalized_insight(
        self, financial_data: Dict, user_id: str
    ) -> Optional[Dict]:
        """개인화된 인사이트 생성 (HyperCLOVA X 사용)"""
        print(f">> 사용자 {user_id}를 위한 고급 인사이트 생성 시작")
        user_profile = self.data_collector.get_personalized_data(user_id)

        if not self.llm_client.is_available():
            print(">> 사용 가능한 LLM API가 없음. Mock 인사이트로 대체합니다")
            result = self.generate_mock_personalized_insight(
                financial_data, user_profile
            )
            result["analysis_method"] = "Mock 데이터 (LLM API 없음) + Graph RAG + DART"
            result["model_used"] = "Mock (LLM 미사용)"
            return result

        try:
            prompt = self.create_personalized_script_prompt(
                financial_data, user_profile
            )

            provider = self.llm_client.get_current_provider()
            print(f">> {provider} API를 사용하여 인사이트 생성 중...")

            response = self.llm_client.chat_completions_create(
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 한국의 기업 공시 정보와 시장 뉴스를 종합 분석하는 전문 투자 어드바이저입니다. 한국 투자자의 정서와 시장 특성을 깊이 이해하고, 일반인이 접하기 어려운 정보를 바탕으로 차별화된 투자 인사이트를 한국어로 제공합니다.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=3000,
                temperature=0.7,
            )

            if not response:
                print(f">> {provider} API 응답 없음, Mock 인사이트로 대체합니다")
                result = self.generate_mock_personalized_insight(
                    financial_data, user_profile
                )
                result["analysis_method"] = (
                    f"Mock 데이터 ({provider} API 실패) + Graph RAG + DART"
                )
                result["model_used"] = f"Mock (원래 {provider} 시도했으나 실패)"
                return result

            # HyperCLOVA X 응답 처리 (OpenAI 형식 아님)
            script_content = response.get_content().strip()

            return {
                "script": script_content,
                "user_id": user_id,
                "analysis_method": f"실제 {provider} API + Graph RAG + DART Disclosures",
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
                "token_usage": response.get_usage()["total_tokens"],
                "model_used": f"실제 {provider} API",
                "data_sources": {
                    "news_count": len(financial_data.get("news", [])),
                    "disclosure_count": len(financial_data.get("disclosures", [])),
                    "stock_count": len(financial_data.get("stock_data", [])),
                },
            }
        except Exception as e:
            print(f">> 고급 인사이트 생성 실패: {e}, Mock 인사이트로 대체합니다")
            result = self.generate_mock_personalized_insight(
                financial_data, user_profile
            )
            result["analysis_method"] = (
                f"Mock 데이터 (예외 발생: {str(e)[:50]}) + Graph RAG + DART"
            )
            result["model_used"] = "Mock (예외 발생으로 인한 대체)"
            return result

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

        stock_data_map = {}
        for stock in financial_data.get("stock_data", []):
            stock_data_map[stock.symbol] = stock

        total_value = 0
        total_cost = 0
        holdings_analysis = []
        missing_data_count = 0

        print(f">> 포트폴리오 분석: {len(portfolio)}개 보유 종목")

        for holding in portfolio:
            symbol, company_name, shares, avg_price = (
                holding[0],
                holding[1],
                holding[2],
                holding[3],
            )

            print(
                f">> 분석 중: {company_name}({symbol}) - {shares}주, 평균 {avg_price:,}원"
            )

            current_price = None
            data_source = "실제 데이터 없음"

            if symbol in stock_data_map:
                stock_info = stock_data_map[symbol]
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

        total_return = total_value - total_cost
        total_return_percent = (
            (total_return / total_cost) * 100 if total_cost > 0 else 0
        )

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
        """개인화된 뉴스 필터링 (공시 연관성 포함)"""
        news_items = financial_data.get("news", [])
        disclosures = financial_data.get("disclosures", [])

        enhanced_news = []

        for news in news_items:
            relevance_score = news.importance_score

            # 공시와 연관성 체크
            for disclosure in disclosures:
                if disclosure.company in news.title:
                    relevance_score += 1.0

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

        enhanced_news.sort(key=lambda x: x["relevance_score"], reverse=True)
        return enhanced_news[:5]

    def generate_mock_personalized_insight(
        self, financial_data: Dict, user_profile: Dict
    ) -> Dict:
        """Mock 개인화 인사이트 생성 (HyperCLOVA X 스타일 - 개선된 버전)"""
        portfolio_analysis = self._analyze_portfolio_performance(
            user_profile, financial_data
        )
        graph_analysis = self.graph_rag.create_market_narrative(financial_data)

        top_entity_info = "분석된 핵심 엔티티가 없습니다."
        if graph_analysis and graph_analysis.get("market_summary", {}).get(
            "top_entities"
        ):
            top_entity = graph_analysis["market_summary"]["top_entities"][0]
            top_entity_info = f"{top_entity[0]}이(가) 가장 주목받는 핵심 요소로 분석되었습니다 (중요도: {top_entity[1]}점)."

        # 실제 주식 데이터 기반 분석
        market_analysis = ""
        if financial_data.get("stock_data"):
            positive_stocks = []
            negative_stocks = []
            for stock in financial_data.get("stock_data", []):
                if stock.change_percent > 0:
                    positive_stocks.append(
                        f"{stock.symbol}(+{stock.change_percent:.1f}%)"
                    )
                else:
                    negative_stocks.append(
                        f"{stock.symbol}({stock.change_percent:.1f}%)"
                    )

            if positive_stocks:
                market_analysis += f"상승세를 보이는 {', '.join(positive_stocks[:2])} 등이 시장을 견인하고 있으며, "
            if negative_stocks:
                market_analysis += (
                    f"{', '.join(negative_stocks[:2])} 등은 조정 압력을 받고 있습니다."
                )

        # 포트폴리오 성과 기반 개인화 메시지
        portfolio_message = ""
        if portfolio_analysis.get("total_return_percent", 0) > 0:
            portfolio_message = f"귀하의 포트폴리오는 현재 {portfolio_analysis.get('total_return_percent', 0):.2f}%의 양호한 수익률을 기록하고 있어 시장 대비 선방하고 있습니다."
        elif portfolio_analysis.get("total_return_percent", 0) < -5:
            portfolio_message = f"포트폴리오 수익률이 {portfolio_analysis.get('total_return_percent', 0):.2f}%로 다소 부진한 상황이지만, 현재 시장 조정기를 감안할 때 중장기 관점에서 접근하시길 권합니다."
        else:
            portfolio_message = f"포트폴리오 수익률 {portfolio_analysis.get('total_return_percent', 0):.2f}%로 시장과 비슷한 움직임을 보이고 있습니다."

        # HyperCLOVA X 스타일의 고품질 한국어 Mock 인사이트
        script = f"""
안녕하세요. 오늘의 맞춤형 투자 인사이트를 전해드립니다.

현재 시장은 혼조세 속에서도 구조적 변화의 신호를 보내고 있습니다. {market_analysis} {top_entity_info}

{portfolio_message}

특히 주목할 점은 AI와 반도체 섹터의 펀더멘털 개선입니다. 네이버의 하이퍼클로바X 상용화가 본격화되면서 관련 생태계 기업들의 수혜가 예상되고, 삼성전자와 SK하이닉스의 HBM 시장 선점 경쟁이 치열해지고 있어 메모리 업계의 재평가 국면이 지속될 것으로 보입니다.

단기적으로는 미국 연준의 통화정책 방향성과 중국 경제 회복 속도가 변수가 될 것이며, 특히 2분기 실적 시즌을 앞두고 개별 기업의 가이던스에 주목하시길 바랍니다.

리스크 관리 차원에서 포지션 크기 조절과 분산투자 원칙을 견지하시되, 장기 성장 동력이 확실한 기술주 비중은 유지하시길 권합니다.

다음 주 주요 모니터링 포인트로는 한국은행 금통위 결과와 주요 기업들의 1분기 실적 발표가 있겠습니다.

감사합니다.
"""

        return {
            "script": script.strip(),
            "user_id": "mock_user",
            "analysis_method": "Mock HyperCLOVA-X + Graph RAG + DART + Real Market Data",
            "portfolio_analysis": portfolio_analysis,
            "personalized_news": [],
            "investment_opportunities": [],
            "graph_analysis": graph_analysis,
            "model_used": "Mock-HyperCLOVA-X",
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

    # === 핵심 수정: 메서드명 변경으로 중복 해결 ===

    async def generate_comprehensive_insight_async(
        self, user_id: str, refresh_data: bool = False
    ) -> Dict:
        """비동기 인사이트 생성 (FastAPI용) - 메서드명 변경"""
        print(f">> 사용자 {user_id}를 위한 종합 인사이트 생성 시작 (비동기)")

        try:
            # 데이터 수집 (비동기 버전 사용)
            financial_data = await self.data_collector.collect_all_data_async(
                user_id=user_id, refresh_cache=refresh_data, use_playwright=True
            )

            # 기존 인사이트 생성 로직 재사용
            comprehensive_script = self._generate_comprehensive_script(
                financial_data=financial_data, user_id=user_id
            )

            # 나머지 분석들
            user_profile = financial_data.get("personalized", {})

            portfolio_analysis = self._analyze_portfolio_performance(
                user_profile, financial_data
            )

            personalized_news = self._filter_personalized_news(
                financial_data, user_profile
            )

            disclosure_insights = self._analyze_disclosure_for_portfolio(
                financial_data.get("disclosures", []),
                set(holding[0] for holding in user_profile.get("portfolio", [])),
            )

            graph_analysis = self.graph_rag.create_market_narrative(financial_data)

            # 결과 반환
            result = {
                "script": comprehensive_script,
                "script_length": len(comprehensive_script),
                "estimated_reading_time": f"약 {max(1, len(comprehensive_script) // 200)}분",
                "analysis_method": "Graph RAG + 실시간 데이터 + 개인화 분석 (비동기)",
                "portfolio_analysis": portfolio_analysis,
                "personalized_news": personalized_news,
                "disclosure_insights": disclosure_insights,
                "graph_analysis": graph_analysis,
                "token_usage": getattr(self, "_last_token_usage", 0),
                "model_used": getattr(self, "_current_model", "HyperCLOVA-X"),
                "data_sources": financial_data.get("data_sources", {}),
            }

            print(f">> 비동기 인사이트 생성 완료: {len(comprehensive_script)}자")
            return result

        except Exception as e:
            print(f">> 비동기 인사이트 생성 실패: {str(e)}")
            raise e

    def generate_comprehensive_insight(
        self, user_id: str, refresh_data: bool = False
    ) -> Dict:
        """기존 동기 인사이트 생성 (하위 호환성 유지)"""
        print(f">> 사용자 {user_id}를 위한 종합 인사이트 생성 시작 (동기)")

        try:
            # 데이터 수집 (동기 버전 사용 - Playwright는 스레드에서 실행)
            financial_data = self.data_collector.collect_all_data(
                user_id=user_id, refresh_cache=refresh_data, use_playwright=True
            )

            # 기존 인사이트 생성 로직 재사용
            comprehensive_script = self._generate_comprehensive_script(
                financial_data=financial_data, user_id=user_id
            )

            # 나머지 분석들
            user_profile = financial_data.get("personalized", {})

            portfolio_analysis = self._analyze_portfolio_performance(
                user_profile, financial_data
            )

            personalized_news = self._filter_personalized_news(
                financial_data, user_profile
            )

            disclosure_insights = self._analyze_disclosure_for_portfolio(
                financial_data.get("disclosures", []),
                set(holding[0] for holding in user_profile.get("portfolio", [])),
            )

            graph_analysis = self.graph_rag.create_market_narrative(financial_data)

            result = {
                "script": comprehensive_script,
                "script_length": len(comprehensive_script),
                "estimated_reading_time": f"약 {max(1, len(comprehensive_script) // 200)}분",
                "analysis_method": "Graph RAG + 실시간 데이터 + 개인화 분석 (동기)",
                "portfolio_analysis": portfolio_analysis,
                "personalized_news": personalized_news,
                "disclosure_insights": disclosure_insights,
                "graph_analysis": graph_analysis,
                "token_usage": getattr(self, "_last_token_usage", 0),
                "model_used": getattr(self, "_current_model", "HyperCLOVA-X"),
                "data_sources": financial_data.get("data_sources", {}),
            }

            print(f">> 동기 인사이트 생성 완료: {len(comprehensive_script)}자")
            return result

        except Exception as e:
            print(f">> 동기 인사이트 생성 실패: {str(e)}")
            raise e

    def _generate_comprehensive_script(self, financial_data: Dict, user_id: str) -> str:
        """통합 스크립트 생성 (기존 로직 재사용)"""
        # 기존 generate_personalized_insight 로직 사용
        insight_result = self.generate_personalized_insight(financial_data, user_id)

        if insight_result and insight_result.get("script"):
            return insight_result["script"]
        else:
            # Mock 인사이트로 폴백
            user_profile = self.data_collector.get_personalized_data(user_id)
            mock_result = self.generate_mock_personalized_insight(
                financial_data, user_profile
            )
            return mock_result.get("script", "인사이트 생성에 실패했습니다.")
