from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from ...services.core.enhanced_rag_workflow import EnhancedRAGWorkflow
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# 전역 워크플로우 인스턴스 (lazy loading)
_enhanced_workflow = None


def get_enhanced_workflow():
    """EnhancedRAGWorkflow 인스턴스를 lazy loading으로 가져오기"""
    global _enhanced_workflow
    if _enhanced_workflow is None:
        try:
            _enhanced_workflow = EnhancedRAGWorkflow()
            logger.info("EnhancedRAGWorkflow 초기화 완료")
        except Exception as e:
            logger.error(f"EnhancedRAGWorkflow 초기화 실패: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail=f"RAG 워크플로우 서비스를 사용할 수 없습니다: {str(e)}",
            )
    return _enhanced_workflow


class ChatQueryRequest(BaseModel):
    query: str
    conversation_id: str = None
    user_id: str = "default_user"
    user_context: dict = None


@router.get("/stream")
async def chat_stream(
    query: str = Query(..., description="사용자 질문"),
    conversation_id: Optional[str] = Query(None, description="대화 ID"),
    user_id: str = Query("default_user", description="사용자 ID"),
    user_name: Optional[str] = Query(None, description="사용자 이름"),
    user_context: Optional[str] = Query(None, description="사용자 컨텍스트 JSON"),
):
    """SSE를 통한 스트리밍 채팅 응답"""

    async def generate_response():
        try:
            # 사용자 컨텍스트 파싱
            parsed_user_context = {}
            if user_context:
                try:
                    parsed_user_context = json.loads(user_context)
                except json.JSONDecodeError:
                    logger.warning(f"사용자 컨텍스트 파싱 실패: {user_context}")
            
            # 사용자 정보 추가
            if user_name:
                parsed_user_context['user_name'] = user_name
            
            logger.info(f"채팅 요청 - 사용자: {user_id} ({user_name}), 질문: {query[:50]}...")
            
            # EnhancedRAGWorkflow를 lazy loading으로 가져오기
            workflow = get_enhanced_workflow()

            # 시작 상태 전송
            yield f"data: {json.dumps({'status': 'processing', 'message': '답변을 생성하고 있습니다...', 'step': 'start'}, ensure_ascii=False)}\n\n"

            # 진행 상황 콜백 함수
            async def progress_callback(step: str, message: str, data: dict = None):
                progress_data = {
                    "status": "processing",
                    "step": step,
                    "message": message,
                }
                if data:
                    progress_data["data"] = data
                yield f"data: {json.dumps(progress_data, ensure_ascii=False)}\n\n"

            # 워크플로우 실행 (진행 상황 콜백과 함께)
            async for progress in workflow.chat_with_progress(
                query=query, user_id=user_id, user_context=parsed_user_context
            ):
                yield f"data: {json.dumps(progress, ensure_ascii=False)}\n\n"

        except HTTPException as he:
            # HTTPException은 그대로 전파
            raise he
        except Exception as e:
            logger.error(f"채팅 스트리밍 중 오류: {str(e)}")
            error_response = {"error": str(e), "status": "error"}
            yield f"data: {json.dumps(error_response, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )


# 기존 POST 엔드포인트도 유지 (다른 용도로 사용 가능)
@router.post("/")
async def chat_post(request: ChatQueryRequest):
    """일반 POST 채팅 (스트리밍 아님)"""
    try:
        # EnhancedRAGWorkflow를 lazy loading으로 가져오기
        workflow = get_enhanced_workflow()
        result = await workflow.chat(query=request.query, user_id=request.user_id)
        return {"response": result, "success": True}
    except HTTPException:
        # HTTPException은 그대로 전파
        raise
    except Exception as e:
        logger.error(f"채팅 처리 중 오류: {str(e)}")
        return {"error": str(e), "success": False}
