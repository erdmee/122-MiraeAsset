#!/usr/bin/env python3
"""
미래에셋 AI 페스티벌 종합 테스트 시스템 (인사이트 출력 포함)
- 생성된 인사이트 스크립트 내용을 실제로 출력합니다.
"""

import sys
import os
import json
from datetime import datetime
import traceback
import pprint

# 프로젝트 루트 경로를 sys.path에 추가하여 app 모듈을 찾을 수 있도록 함
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.enhanced_data_collector import EnhancedDataCollector
from app.services.personalized_insight_generator import PersonalizedInsightGenerator
from app.services.simple_graph_rag import SimpleGraphRAG
from app.models.user_models import (
    UserProfile,
    StockHolding,
    UserPreferences,
    RiskLevel,
    InvestmentStyle,
    StockPrice,
)
from app.models.responses import NewsItem, DisclosureItem


class ComprehensiveTestSystem:
    """종합 테스트 시스템 클래스"""

    def __init__(self):
        """초기화 함수: 각 서비스 모듈을 인스턴스화하고 테스트 사용자를 생성합니다."""
        self.data_collector = EnhancedDataCollector()
        self.insight_generator = PersonalizedInsightGenerator()
        self.graph_rag = SimpleGraphRAG()
        self.test_users = self.create_test_users()
        print(">> 종합 테스트 시스템 초기화 완료")

    def create_test_users(self) -> dict:
        """테스트 목적의 다양한 사용자 프로필 3개를 생성합니다."""
        print(">> 테스트 사용자 프로필 생성 중...")
        test_users = {}

        # 사용자 1: AI 관련 주식에 관심이 많은 성장형 투자자
        ai_investor = UserProfile(
            user_id="ai_investor_001",
            name="성민",
            age=25,
            investment_experience="2년",
            portfolio=[
                StockHolding(
                    symbol="005930",
                    company_name="삼성전자",
                    shares=10,
                    avg_price=70000,
                    sector="반도체",
                ),
                StockHolding(
                    symbol="000660",
                    company_name="SK하이닉스",
                    shares=5,
                    avg_price=120000,
                    sector="반도체",
                ),
                StockHolding(
                    symbol="035420",
                    company_name="NAVER",
                    shares=3,
                    avg_price=200000,
                    sector="IT",
                ),
            ],
            preferences=UserPreferences(
                preferred_sectors=["AI", "반도체", "IT", "소프트웨어"],
                risk_level=RiskLevel.HIGH,
                investment_style=InvestmentStyle.GROWTH,
                news_keywords=["AI", "인공지능", "ChatGPT", "NVIDIA", "반도체"],
            ),
        )

        test_users["ai_investor"] = ai_investor
        print(">> 1명의 테스트 사용자 생성 완료 (AI 투자자)")
        return test_users

    def _validate_data_quality(self, financial_data: dict):
        """수집된 데이터의 포맷과 내용의 유효성을 검증합니다."""
        print("\n--- 데이터 품질 검증 시작 ---")
        errors = []
        warnings = []

        # 뉴스 데이터 검증
        if not financial_data.get("news"):
            warnings.append(">> 뉴스 데이터가 없습니다.")
        elif not isinstance(financial_data["news"][0], NewsItem):
            errors.append(">> 뉴스 데이터 형식에 문제가 있습니다.")

        # 공시 데이터 검증
        if not financial_data.get("disclosures"):
            warnings.append(">> 공시 데이터가 없습니다.")
        elif not isinstance(financial_data["disclosures"][0], DisclosureItem):
            errors.append(">> 공시 데이터 형식에 문제가 있습니다.")

        # 주식 데이터 검증
        if not financial_data.get("stock_data"):
            errors.append(">> 주식 데이터가 없습니다.")
        elif not isinstance(financial_data["stock_data"][0], StockPrice):
            errors.append(">> 주식 데이터 형식에 문제가 있습니다.")

        if not errors and not warnings:
            print(">> 모든 데이터 품질이 정상입니다.")
        else:
            for warning in warnings:
                print(warning)
            for error in errors:
                print(error)
        print("--- 데이터 품질 검증 종료 ---\n")

    def test_step_1_data_collection(self):
        """1단계: 데이터 수집 모듈을 테스트합니다."""
        print("=" * 80)
        print(">> 1단계: 실제 데이터 수집 테스트")
        print("=" * 80)
        try:
            financial_data = self.data_collector.collect_all_data(
                user_id="ai_investor_001", refresh_cache=True
            )
            self._validate_data_quality(financial_data)
            return financial_data
        except Exception as e:
            print(f">> 데이터 수집 중 심각한 오류 발생: {e}")
            traceback.print_exc()
            return None

    def test_step_2_personalized_insights(self, financial_data: dict):
        """2단계: 개인화된 인사이트 생성 모듈을 테스트합니다."""
        print("\n" + "=" * 80)
        print(">> 2단계: 개인화된 인사이트 생성 테스트")
        print("=" * 80)
        if not financial_data:
            print(">> 이전 단계 실패로 테스트를 건너뜁니다.")
            return None

        insights_results = {}

        # AI 투자자만 테스트 (간소화)
        user_profile = self.test_users["ai_investor"]
        print(f"\n--- {user_profile.name}(AI 투자자) 인사이트 생성 ---")

        try:
            # 사용자 정보 저장
            portfolio_data = [h.model_dump() for h in user_profile.portfolio]
            self.insight_generator.save_user_portfolio(
                user_profile.user_id, portfolio_data
            )
            preferences_data = user_profile.preferences.model_dump()
            self.insight_generator.save_user_preferences(
                user_profile.user_id, preferences_data
            )

            # 인사이트 생성
            insight_result = self.insight_generator.generate_comprehensive_insight(
                user_profile.user_id, refresh_data=False
            )

            if insight_result:
                insights_results["ai_investor"] = insight_result
                print(
                    f">> AI 투자자 인사이트 생성 완료 (스크립트 길이: {insight_result.get('script_length', 0)}자)"
                )

                # FIX: 실제 인사이트 스크립트 내용 출력
                print("\n" + "=" * 80)
                print("- 생성된 AI 투자 인사이트 스크립트")
                print("=" * 80)
                script_content = insight_result.get(
                    "script", "스크립트가 생성되지 않았습니다."
                )
                print(script_content)
                print("=" * 80)

                # 포트폴리오 분석 결과 출력
                print("\n>> 포트폴리오 분석 상세 결과:")
                portfolio_analysis = insight_result.get("portfolio_analysis", {})

                if portfolio_analysis.get("data_quality_warning"):
                    print(f">> {portfolio_analysis['data_quality_warning']}")

                if portfolio_analysis.get("analyzed_holdings_count", 0) > 0:
                    print(
                        f"   - 분석 가능 종목: {portfolio_analysis['analyzed_holdings_count']}개"
                    )
                    print(
                        f"   - 총 투자금: {portfolio_analysis.get('total_cost', 0):,}원"
                    )
                    print(
                        f"   - 총 평가액: {portfolio_analysis.get('total_value', 0):,}원"
                    )
                    print(
                        f"   - 총 수익률: {portfolio_analysis.get('total_return_percent', 0):+.2f}%"
                    )

                    # 개별 종목 상세 정보
                    print("\n   >> 개별 종목 분석:")
                    for holding in portfolio_analysis.get("holdings_detail", []):
                        if holding.get("current_price"):
                            print(
                                f"      - {holding['company_name']}: {holding['return_percent']:+.2f}% ({holding['data_source']})"
                            )
                        else:
                            print(
                                f"      - {holding['company_name']}: 데이터 없음 ({holding.get('error', '알 수 없는 오류')})"
                            )
                else:
                    print(
                        "   >> 실시간 데이터 부족으로 포트폴리오 분석을 할 수 없습니다."
                    )

            else:
                print(">> 인사이트 생성 실패")

        except Exception as e:
            print(f">> AI 투자자 인사이트 생성 실패: {e}")
            traceback.print_exc()

        return insights_results

    def test_step_3_graph_rag_analysis(self, financial_data: dict):
        """3단계: Graph RAG 분석 모듈을 테스트합니다."""
        print("\n" + "=" * 80)
        print(">> 3단계: Graph RAG 분석 테스트")
        print("=" * 80)
        if not financial_data:
            print("- 이전 단계 실패로 테스트를 건너뜁니다.")
            return None
        try:
            narrative = self.graph_rag.create_market_narrative(financial_data)
            print("- Graph RAG 분석 완료:")

            # 상위 엔티티 출력
            print("\n>> 상위 중요 엔티티:")
            top_entities = narrative["market_summary"]["top_entities"]
            if top_entities:
                for i, (entity, score) in enumerate(top_entities[:5], 1):
                    print(f"   {i}. {entity}: {score}점")
            else:
                print(" >> 분석된 엔티티가 없습니다.")

            # 주요 테마 출력
            print("\n- 주요 테마:")
            main_themes = narrative["market_summary"]["main_themes"]
            if main_themes:
                for i, theme in enumerate(main_themes[:3], 1):
                    entities_str = ", ".join(theme["entities"])
                    print(f"   {i}. {theme['theme']}: {entities_str}")
            else:
                print("  >> 분석된 테마가 없습니다.")

            return narrative
        except Exception as e:
            print(f">> Graph RAG 분석 실패: {e}")
            traceback.print_exc()
            return None

    def run_focused_test(self):
        """핵심 기능만 테스트 (인사이트 내용 확인 중심)"""
        start_time = datetime.now()
        print(
            f"미래에셋 AI 인사이트 핵심 테스트 시작: {start_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        # 1단계: 데이터 수집
        financial_data = self.test_step_1_data_collection()

        if financial_data:
            # 2단계: 인사이트 생성 (핵심!)
            insights = self.test_step_2_personalized_insights(financial_data)

            # 3단계: Graph RAG 분석
            self.test_step_3_graph_rag_analysis(financial_data)

        end_time = datetime.now()
        print("\n" + "=" * 80)
        print(
            f"핵심 테스트 완료: {end_time.strftime('%Y-%m-%d %H:%M:%S')} (총 소요 시간: {end_time - start_time})"
        )
        print("=" * 80)


if __name__ == "__main__":
    test_system = ComprehensiveTestSystem()
    test_system.run_focused_test()
