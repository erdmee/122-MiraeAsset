#!/usr/bin/env python3
"""
인사이트 생성 과정 디버깅 테스트
"""

import sys
import os
import traceback
from datetime import datetime

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.personalized_insight_generator import PersonalizedInsightGenerator
from app.services.enhanced_data_collector import EnhancedDataCollector


def debug_insight_generation():
    """인사이트 생성 과정을 단계별로 디버깅"""
    print(">> 인사이트 생성 과정 디버깅 시작")

    try:
        # 1. 데이터 수집기 초기화
        print("\n> 데이터 수집기 초기화...")
        data_collector = EnhancedDataCollector()
        print("데이터 수집기 초기화 완료")

        # 2. 인사이트 생성기 초기화
        print("\n> 인사이트 생성기 초기화...")
        insight_generator = PersonalizedInsightGenerator()
        print("인사이트 생성기 초기화 완료")

        # 3. 간단한 금융 데이터 수집
        print("\n> 기본 금융 데이터 수집...")
        financial_data = {
            "news": [],
            "disclosures": [],
            "stock_data": [],
            "collected_at": datetime.now().isoformat(),
        }

        # 뉴스 수집 시도
        try:
            news_items = data_collector.collect_comprehensive_news(limit=3)
            financial_data["news"] = news_items
            print(f"- 뉴스 {len(news_items)}건 수집")
        except Exception as e:
            print(f"- 뉴스 수집 실패: {e}")

        # 4. Mock 사용자 프로필 생성
        print("\n> 테스트 사용자 프로필 설정...")
        user_id = "debug_user_001"

        # 간단한 포트폴리오 설정
        portfolio_data = [
            {
                "symbol": "005930",
                "company_name": "삼성전자",
                "shares": 10,
                "avg_price": 70000,
                "sector": "반도체",
            }
        ]

        # 사용자 선호도 설정
        preferences_data = {
            "preferred_sectors": ["반도체", "AI"],
            "risk_level": "고위험",
            "investment_style": "성장형",
            "news_keywords": ["삼성전자", "반도체"],
        }

        # DB에 저장
        insight_generator.save_user_portfolio(user_id, portfolio_data)
        insight_generator.save_user_preferences(user_id, preferences_data)
        print(">> 사용자 프로필 설정 완료")

        # 5. 인사이트 생성 시도
        print("\n>> 개인화 인사이트 생성 시도...")
        print("> 사용할 데이터:")
        print(f"   - 뉴스: {len(financial_data['news'])}건")
        print(f"   - 공시: {len(financial_data['disclosures'])}건")
        print(f"   - 주식: {len(financial_data['stock_data'])}건")

        try:
            print("\n> OpenAI API 호출 중...")
            insight_result = insight_generator.generate_personalized_insight(
                financial_data, user_id
            )

            if insight_result:
                print(">> 인사이트 생성 성공!")
                print(f"- 스크립트 길이: {len(insight_result.get('script', ''))}자")
                print(
                    f"- 분석 방법: {insight_result.get('analysis_method', 'Unknown')}"
                )
                print(f"- 사용 모델: {insight_result.get('model_used', 'Unknown')}")

                # 실제 스크립트 내용 출력
                script = insight_result.get("script", "")
                if script:
                    print("\n" + "=" * 80)
                    print(">> 생성된 인사이트 스크립트:")
                    print("=" * 80)
                    print(script)
                    print("=" * 80)
                else:
                    print("<< 스크립트 내용이 비어있습니다.")

            else:
                print("<< 인사이트 생성 실패 - None 반환")

        except Exception as e:
            print(f"<< 인사이트 생성 중 오류: {e}")
            traceback.print_exc()

        print("\n>>> 디버깅 테스트 완료")

    except Exception as e:
        print(f"<<< 전체 테스트 실패: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    debug_insight_generation()
