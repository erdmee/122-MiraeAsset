# app/api/routes/insights.py
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.services.personalized_insight_generator import PersonalizedInsightGenerator
from app.services.simple_graph_rag import SimpleGraphRAG
from app.services.enhanced_data_collector import EnhancedDataCollector

router = APIRouter()
insight_generator = PersonalizedInsightGenerator()
graph_rag = SimpleGraphRAG()
data_collector = EnhancedDataCollector()


@router.post("/generate/{user_id}")
async def generate_personalized_insight(
    user_id: str,
    refresh_data: bool = Query(default=False, description="데이터 새로고침 여부"),
):
    """개인화된 AI 투자 인사이트 생성"""
    try:
        insight_result = insight_generator.generate_comprehensive_insight(
            user_id=user_id, refresh_data=refresh_data
        )

        if not insight_result:
            raise HTTPException(status_code=404, detail="인사이트 생성 실패")

        return {
            "user_id": user_id,
            "script": insight_result.get("script"),
            "script_length": insight_result.get("script_length"),
            "estimated_reading_time": insight_result.get("estimated_reading_time"),
            "analysis_method": insight_result.get("analysis_method"),
            "portfolio_analysis": insight_result.get("portfolio_analysis"),
            "personalized_news": insight_result.get("personalized_news"),
            "disclosure_insights": insight_result.get("disclosure_insights"),
            "graph_analysis": insight_result.get("graph_analysis"),
            "token_usage": insight_result.get("token_usage"),
            "model_used": insight_result.get("model_used"),
            "data_sources": insight_result.get("data_sources"),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"인사이트 생성 실패: {str(e)}")


@router.get("/portfolio-analysis/{user_id}")
async def get_portfolio_analysis(user_id: str):
    """사용자 포트폴리오 분석"""
    try:
        # 사용자 데이터 및 최신 시장 데이터 수집
        financial_data = data_collector.collect_all_data(user_id=user_id)
        user_profile = data_collector.get_personalized_data(user_id)

        # 포트폴리오 분석 수행
        portfolio_analysis = insight_generator._analyze_portfolio_performance(
            user_profile, financial_data
        )

        return {
            "user_id": user_id,
            "portfolio_analysis": portfolio_analysis,
            "analyzed_at": financial_data.get("collected_at"),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"포트폴리오 분석 실패: {str(e)}")


@router.get("/graph-analysis")
async def get_graph_rag_analysis(
    user_id: Optional[str] = Query(default=None, description="사용자 ID (선택사항)")
):
    """Graph RAG 시장 분석"""
    try:
        # 최신 금융 데이터 수집
        financial_data = data_collector.collect_all_data(user_id=user_id)

        # Graph RAG 분석 수행
        market_narrative = graph_rag.create_market_narrative(financial_data)

        return {
            "market_analysis": market_narrative,
            "analyzed_at": financial_data.get("collected_at"),
            "data_sources": financial_data.get("data_sources"),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph RAG 분석 실패: {str(e)}")


@router.get("/news-insights")
async def get_personalized_news_insights(
    user_id: str, limit: int = Query(default=10, ge=1, le=50, description="뉴스 개수")
):
    """개인화된 뉴스 인사이트"""
    try:
        # 사용자 맞춤 데이터 수집
        financial_data = data_collector.collect_all_data(user_id=user_id)
        user_profile = data_collector.get_personalized_data(user_id)

        # 개인화된 뉴스 필터링
        personalized_news = insight_generator._filter_personalized_news(
            financial_data, user_profile
        )

        return {
            "user_id": user_id,
            "personalized_news": personalized_news[:limit],
            "total_news_count": len(financial_data.get("news", [])),
            "filtered_count": len(personalized_news),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"뉴스 인사이트 생성 실패: {str(e)}"
        )


@router.get("/disclosure-analysis/{user_id}")
async def get_disclosure_analysis(user_id: str):
    """사용자 맞춤 공시 분석"""
    try:
        # 데이터 수집
        financial_data = data_collector.collect_all_data(user_id=user_id)
        user_profile = data_collector.get_personalized_data(user_id)

        # 포트폴리오 종목 추출
        portfolio_symbols = set()
        if user_profile.get("portfolio"):
            portfolio_symbols = {holding[0] for holding in user_profile["portfolio"]}

        # 공시 분석 수행
        disclosure_analysis = insight_generator._analyze_disclosure_for_portfolio(
            financial_data.get("disclosures", []), portfolio_symbols
        )

        # 공시-뉴스 연관성 분석
        cross_analysis = insight_generator._analyze_disclosure_news_correlation(
            financial_data.get("disclosures", []), financial_data.get("news", [])
        )

        return {
            "user_id": user_id,
            "disclosure_analysis": disclosure_analysis,
            "cross_analysis": cross_analysis,
            "portfolio_symbols": list(portfolio_symbols),
            "total_disclosures": len(financial_data.get("disclosures", [])),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"공시 분석 실패: {str(e)}")


@router.get("/test")
async def test_insight_generation():
    """인사이트 생성 기능 테스트"""
    try:
        # 테스트용 더미 데이터
        test_data = {
            "news": [],
            "disclosures": [],
            "stock_data": [],
            "personalized": {"portfolio": [], "preferences": {}},
        }

        # Graph RAG 테스트
        narrative = graph_rag.create_market_narrative(test_data)

        return {
            "status": "success",
            "message": "인사이트 생성 테스트 완료",
            "graph_rag_result": narrative["market_summary"] if narrative else None,
        }

    except Exception as e:
        return {"status": "error", "message": f"테스트 실패: {str(e)}"}
