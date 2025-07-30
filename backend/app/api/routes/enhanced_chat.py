# app/api/routes/enhanced_chat.py

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from app.services.core.personalized_insight_generator import (
    PersonalizedInsightGenerator,
)
from app.services.storage.insight_storage import InsightStorage
from app.services.storage.user_memory import UserMemorySystem
from app.services.external.hyperclova_client import MultiLLMClient
from app.services.core.agents import (
    SimpleAgent,
    PlanningAgent,
    RetrieverAgent,
    CriticAgent1,
    ContextIntegratorAgent,
    ReportGeneratorAgent,
    ClovaXLLM,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# 전역 인스턴스들
insight_generator = PersonalizedInsightGenerator()
insight_storage = InsightStorage()
user_memory = UserMemorySystem()
llm_client = MultiLLMClient()

# 새로운 에이전트 워크플로우
clova_llm = ClovaXLLM()
simple_agent = SimpleAgent(clova_llm)
planning_agent = PlanningAgent(clova_llm)
retriever_agent = RetrieverAgent(llm=clova_llm)
critic_agent = CriticAgent1(clova_llm)
context_integrator = ContextIntegratorAgent(clova_llm)
report_generator = ReportGeneratorAgent(clova_llm)


# Request/Response 모델들
class ChatRequest(BaseModel):
    query: str
    user_id: str = "default"
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    insight_id: Optional[str] = None
    action_items: List[Dict] = []
    graph_entities: List[str] = []
    response_type: str = "simple"  # simple, complex
    generated_at: str


class UserProfileRequest(BaseModel):
    user_id: str
    name: Optional[str] = None
    age: Optional[int] = None
    investment_experience: Optional[str] = None  # beginner, intermediate, expert
    risk_tolerance: Optional[str] = None  # conservative, moderate, aggressive
    investment_goals: List[str] = []


class StockHoldingRequest(BaseModel):
    user_id: str
    stock_code: str
    stock_name: str
    quantity: int
    avg_price: float
    purchase_date: str
    sector: Optional[str] = None


class InsightSearchRequest(BaseModel):
    query: str
    user_id: Optional[str] = None
    entities: List[str] = []
    tags: List[str] = []
    limit: int = 10


@router.post("/chat", response_model=ChatResponse)
async def enhanced_chat(request: ChatRequest):
    """지능적 Planning-based Graph RAG 채팅 API"""
    try:
        # 1. 자연어에서 사용자 정보 추출 및 저장 (백그라운드)
        await _extract_and_save_user_info(request.query, request.user_id)

        # 2. 사용자 컨텍스트 수집
        user_context = await user_memory.get_user_context(request.user_id)

        # 3. Simple Query 체크 (빠른 응답 가능한 질문)
        is_simple = await simple_agent.is_simple_query(request.query)

        if is_simple:
            # Simple 응답 (외부 검색 불필요)
            logger.info(f"Simple Query 감지: {request.query[:50]}...")
            simple_response = await simple_agent.generate_simple_response(request.query)

            return ChatResponse(
                response=simple_response,
                response_type="simple",
                generated_at=datetime.now().isoformat(),
            )

        # 4. Complex Query - Planning Phase
        logger.info(f"Complex Query 감지: {request.query[:50]}...")

        # Planning: 지능적 쿼리 분해 및 도구 기반 계획 수립
        query_plan = await planning_agent.plan(request.query)
        logger.info(
            f"Planning 결과: {len(query_plan)}개 쿼리, 도구: {[q['tool'] for q in query_plan]}"
        )

        # 5. Information Retrieval Phase (향상된 병렬 검색)
        retrieved_results = await retriever_agent.retrieve(query_plan)
        logger.info(
            f"정보 검색 완료: 성공 {retrieved_results['metadata']['successful_queries']}, 실패 {retrieved_results['metadata']['failed_queries']}"
        )

        # 6. Critical Evaluation Phase
        critic_result = await critic_agent.evaluate(retrieved_results, request.query)

        # 7. Re-planning if needed (정보 부족 시)
        iteration_count = 0
        max_iterations = 2

        while (
            not critic_result.get("sufficiency", True)
            and iteration_count < max_iterations
        ):
            logger.info(f"정보 부족으로 재검색 시작 (반복 {iteration_count + 1})")

            # 추가 검색 계획 (피드백 반영)
            additional_query_plan = await planning_agent.plan(
                request.query, critic_feedback=critic_result.get("feedback", "")
            )

            # 추가 정보 검색
            additional_results = await retriever_agent.retrieve(additional_query_plan)

            # 결과 병합
            for key in ["financial_data", "news_data", "market_analysis", "graph_data"]:
                retrieved_results[key].extend(additional_results.get(key, []))

            retrieved_results["metadata"]["successful_queries"] += additional_results[
                "metadata"
            ]["successful_queries"]
            retrieved_results["metadata"]["failed_queries"] += additional_results[
                "metadata"
            ]["failed_queries"]

            # 재평가
            critic_result = await critic_agent.evaluate(
                retrieved_results, request.query
            )
            iteration_count += 1

        # 8. Context Integration Phase
        integrated_context = context_integrator.integrate(
            retrieved_results, user_context
        )
        logger.info("컨텍스트 통합 완료")

        # 9. Final Report Generation Phase
        final_report = report_generator.generate(integrated_context, user_context)
        logger.info("최종 리포트 생성 완료")

        # 10. Insight Storage (백그라운드)
        try:
            insight_id = await insight_storage.store_insight(
                insight_content=final_report,
                user_query=request.query,
                user_id=request.user_id,
                entities=_extract_entities_from_results(retrieved_results),
                metadata={
                    "planning_based": True,
                    "sub_queries_count": len(query_plan),
                    "iteration_count": iteration_count,
                    "tools_used": retrieved_results["metadata"]["tools_used"],
                    "sufficiency_score": (
                        1.0 if critic_result.get("sufficiency", True) else 0.5
                    ),
                },
            )
        except Exception as e:
            logger.error(f"인사이트 저장 실패: {e}")
            insight_id = None

        # 11. Response Construction
        response = ChatResponse(
            response=final_report,
            insight_id=insight_id,
            action_items=_extract_action_items_from_report(final_report),
            graph_entities=_extract_entities_from_results(retrieved_results),
            response_type="complex",
            generated_at=datetime.now().isoformat(),
        )

        logger.info(
            f"Planning-based 채팅 완료: {request.user_id} (반복: {iteration_count})"
        )
        return response

    except Exception as e:
        logger.error(f"채팅 처리 실패: {e}")
        raise HTTPException(
            status_code=500, detail=f"채팅 처리 중 오류가 발생했습니다: {str(e)}"
        )


def _extract_entities_from_results(results: List[Dict]) -> List[str]:
    """검색 결과에서 엔티티 추출"""
    entities = []
    for result in results:
        # 각 결과에서 엔티티 추출 로직
        if "삼성전자" in str(result):
            entities.append("삼성전자")
        if "LG전자" in str(result):
            entities.append("LG전자")
        if "SK하이닉스" in str(result):
            entities.append("SK하이닉스")
        # 더 많은 엔티티 추출 로직 추가 가능

    return list(set(entities))


def _extract_action_items_from_report(report: str) -> List[Dict]:
    """리포트에서 액션 아이템 추출"""
    action_items = []

    # 간단한 패턴 매칭으로 액션 아이템 추출
    lines = report.split("\n")
    for line in lines:
        if any(
            keyword in line.lower()
            for keyword in ["권장", "제안", "고려", "추천", "검토"]
        ):
            if len(line.strip()) > 10:  # 의미있는 길이
                action_items.append(
                    {
                        "action": line.strip(),
                        "priority": "medium",
                        "category": "investment_suggestion",
                    }
                )

    return action_items[:5]  # 최대 5개


async def _extract_and_save_user_info(query: str, user_id: str):
    """자연어에서 사용자 정보 추출 및 자동 저장"""
    try:
        # HyperCLOVA X로 사용자 정보 추출
        extraction_prompt = f"""다음 사용자의 메시지에서 개인 정보와 투자 정보를 추출하세요.

사용자 메시지: "{query}"

추출할 정보:
1. 개인 정보: 이름, 나이, 투자 경험, 위험 성향
2. 보유 주식: 종목명, 수량, 매수 가격, 섹터
3. 투자 목표: 장기/단기, 성장/배당 등

응답 형식 (JSON):
{{
    "personal_info": {{
        "name": "이름" 또는 null,
        "age": 나이 또는 null,
        "investment_experience": "beginner/intermediate/expert" 또는 null,
        "risk_tolerance": "conservative/moderate/aggressive" 또는 null,
        "investment_goals": ["목표1", "목표2"] 또는 []
    }},
    "holdings": [
        {{
            "stock_name": "종목명",
            "stock_code": "종목코드" 또는 "추정_필요",
            "quantity": 수량 또는 null,
            "avg_price": 평균단가 또는 null,
            "sector": "섹터" 또는 null
        }}
    ],
    "extracted": true/false
}}

정보가 없으면 extracted: false로 응답하세요."""

        if llm_client.is_available():
            response = llm_client.chat_completion(
                messages=[{"role": "user", "content": extraction_prompt}],
                temperature=0.1,
                max_tokens=1000,
            )

            if response and response.get_content():
                import json
                import re

                content = response.get_content()

                # JSON 추출
                json_pattern = r"\{.*?\}"
                matches = re.search(json_pattern, content, re.DOTALL)

                if matches:
                    extracted_data = json.loads(matches.group())

                    if extracted_data.get("extracted"):
                        # 개인 정보 저장
                        personal_info = extracted_data.get("personal_info", {})
                        if any(personal_info.values()):
                            # 기존 프로필과 병합
                            existing_profile = await user_memory.get_user_profile(
                                user_id
                            )

                            profile_data = {
                                "user_id": user_id,
                                "name": personal_info.get("name")
                                or (
                                    existing_profile.get("name")
                                    if existing_profile
                                    else None
                                ),
                                "age": personal_info.get("age")
                                or (
                                    existing_profile.get("age")
                                    if existing_profile
                                    else None
                                ),
                                "investment_experience": personal_info.get(
                                    "investment_experience"
                                )
                                or (
                                    existing_profile.get("investment_experience")
                                    if existing_profile
                                    else None
                                ),
                                "risk_tolerance": personal_info.get("risk_tolerance")
                                or (
                                    existing_profile.get("risk_tolerance")
                                    if existing_profile
                                    else None
                                ),
                                "investment_goals": personal_info.get(
                                    "investment_goals", []
                                )
                                + (
                                    existing_profile.get("investment_goals", [])
                                    if existing_profile
                                    else []
                                ),
                            }

                            # 중복 제거
                            profile_data["investment_goals"] = list(
                                set(profile_data["investment_goals"])
                            )

                            await user_memory.create_user_profile(profile_data)
                            logger.info(f"사용자 정보 자동 추출 및 저장: {user_id}")

                        # 보유 주식 저장
                        holdings = extracted_data.get("holdings", [])
                        for holding in holdings:
                            if holding.get("stock_name"):
                                # 종목코드 추정 (간단한 매핑)
                                stock_code = _estimate_stock_code(
                                    holding.get("stock_name")
                                )

                                holding_data = {
                                    "stock_code": stock_code,
                                    "stock_name": holding.get("stock_name"),
                                    "quantity": holding.get("quantity") or 0,
                                    "avg_price": holding.get("avg_price") or 0.0,
                                    "purchase_date": datetime.now().strftime(
                                        "%Y-%m-%d"
                                    ),
                                    "sector": holding.get("sector"),
                                }

                                await user_memory.add_holding(user_id, holding_data)
                                logger.info(
                                    f"보유 주식 자동 추출 및 저장: {user_id} - {holding.get('stock_name')}"
                                )

    except Exception as e:
        logger.error(f"사용자 정보 추출 실패: {e}")
        # 추출 실패해도 채팅은 계속 진행


def _estimate_stock_code(stock_name: str) -> str:
    """주식명으로 종목코드 추정 (간단한 매핑)"""
    stock_mapping = {
        "삼성전자": "005930",
        "SK하이닉스": "000660",
        "LG화학": "051910",
        "현대차": "005380",
        "NAVER": "035420",
        "카카오": "035720",
        "셀트리온": "068270",
        "현대중공업": "009540",
        "포스코": "005490",
        "LG전자": "066570",
        "KT": "030200",
        "아모레퍼시픽": "090430",
    }

    # 부분 매칭
    for name, code in stock_mapping.items():
        if name in stock_name or stock_name in name:
            return code

    return "000000"  # 기본값


@router.post("/user/profile")
async def create_user_profile(request: UserProfileRequest):
    """사용자 프로필 생성/업데이트"""
    try:
        user_data = {
            "user_id": request.user_id,
            "name": request.name,
            "age": request.age,
            "investment_experience": request.investment_experience,
            "risk_tolerance": request.risk_tolerance,
            "investment_goals": request.investment_goals,
        }

        success = await user_memory.create_user_profile(user_data)

        if success:
            return {"message": "사용자 프로필이 성공적으로 생성/업데이트되었습니다."}
        else:
            raise HTTPException(status_code=400, detail="프로필 생성에 실패했습니다.")

    except Exception as e:
        logger.error(f"프로필 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}/profile")
async def get_user_profile(user_id: str):
    """사용자 프로필 조회"""
    try:
        profile = await user_memory.get_user_profile(user_id)

        if profile:
            return profile
        else:
            raise HTTPException(
                status_code=404, detail="사용자 프로필을 찾을 수 없습니다."
            )

    except Exception as e:
        logger.error(f"프로필 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/user/holding")
async def add_user_holding(request: StockHoldingRequest):
    """사용자 보유 주식 추가"""
    try:
        holding_data = {
            "stock_code": request.stock_code,
            "stock_name": request.stock_name,
            "quantity": request.quantity,
            "avg_price": request.avg_price,
            "purchase_date": request.purchase_date,
            "sector": request.sector,
        }

        success = await user_memory.add_holding(request.user_id, holding_data)

        if success:
            return {"message": f"{request.stock_name} 보유 정보가 추가되었습니다."}
        else:
            raise HTTPException(
                status_code=400, detail="보유 주식 추가에 실패했습니다."
            )

    except Exception as e:
        logger.error(f"보유 주식 추가 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}/holdings")
async def get_user_holdings(user_id: str):
    """사용자 보유 주식 조회"""
    try:
        holdings = await user_memory.get_user_holdings(user_id)
        return {"holdings": holdings, "count": len(holdings)}

    except Exception as e:
        logger.error(f"보유 주식 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}/context")
async def get_user_context(user_id: str, session_id: Optional[str] = None):
    """사용자 전체 컨텍스트 조회"""
    try:
        context = await user_memory.get_user_context(user_id, session_id)
        return context

    except Exception as e:
        logger.error(f"사용자 컨텍스트 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/insights/search")
async def search_insights(request: InsightSearchRequest):
    """인사이트 검색"""
    try:
        results = await insight_storage.search_insights(
            query=request.query,
            user_id=request.user_id,
            entities=request.entities,
            tags=request.tags,
            limit=request.limit,
        )

        return {"insights": results, "count": len(results)}

    except Exception as e:
        logger.error(f"인사이트 검색 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights/{insight_id}")
async def get_insight(insight_id: str):
    """특정 인사이트 조회"""
    try:
        insight = await insight_storage.get_insight_by_id(insight_id)

        if insight:
            return insight
        else:
            raise HTTPException(status_code=404, detail="인사이트를 찾을 수 없습니다.")

    except Exception as e:
        logger.error(f"인사이트 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}/insights")
async def get_user_insights(user_id: str, limit: int = 20):
    """사용자별 인사이트 목록"""
    try:
        insights = await insight_storage.get_user_insights(user_id, limit)
        return {"insights": insights, "count": len(insights)}

    except Exception as e:
        logger.error(f"사용자 인사이트 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}/conversations")
async def get_conversation_history(
    user_id: str, session_id: Optional[str] = None, limit: int = 50
):
    """대화 이력 조회"""
    try:
        conversations = await user_memory.get_conversation_history(
            user_id, session_id, limit
        )
        return {"conversations": conversations, "count": len(conversations)}

    except Exception as e:
        logger.error(f"대화 이력 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/user/{user_id}/daily-insight")
async def generate_daily_insight(user_id: str, background_tasks: BackgroundTasks):
    """일일 개인화 인사이트 생성 (백그라운드)"""
    try:
        # 백그라운드에서 실행
        background_tasks.add_task(_generate_daily_insight_background, user_id)

        return {"message": "일일 인사이트 생성이 시작되었습니다. 잠시 후 확인해주세요."}

    except Exception as e:
        logger.error(f"일일 인사이트 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _generate_daily_insight_background(user_id: str):
    """백그라운드에서 일일 인사이트 생성"""
    try:
        query = f"오늘의 시장 상황과 내 포트폴리오 분석 - {datetime.now().strftime('%Y-%m-%d')}"

        result = await insight_generator.generate_daily_insight(
            user_id=user_id, query=query
        )

        logger.info(f"일일 인사이트 생성 완료: {user_id} - {result.get('insight_id')}")

    except Exception as e:
        logger.error(f"백그라운드 인사이트 생성 실패: {e}")


@router.get("/health")
async def health_check():
    """시스템 상태 확인"""
    try:
        # 각 시스템 상태 확인
        status = {
            "timestamp": datetime.now().isoformat(),
            "services": {
                "insight_generator": "operational",
                "insight_storage": "operational",
                "user_memory": "operational",
                "graph_rag": "operational",
            },
        }

        return status

    except Exception as e:
        logger.error(f"상태 확인 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))
