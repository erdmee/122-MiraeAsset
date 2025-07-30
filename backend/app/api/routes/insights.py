# app/api/routes/insights.py (개선된 버전)
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
import asyncio
import json
import os
import logging
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from app.services.core.personalized_insight_generator import (
    PersonalizedInsightGenerator,
)
from app.services.core.enhanced_graph_rag import EnhancedGraphRAG
from app.services.storage.enhanced_data_collector import EnhancedDataCollector
from app.services.external.aistudios_service import VideoGenerationService

# 로거 설정
logger = logging.getLogger(__name__)

router = APIRouter()
insight_generator = PersonalizedInsightGenerator()
enhanced_graph_rag = EnhancedGraphRAG()
data_collector = EnhancedDataCollector()

# 환경변수로 비디오 제공자 선택 (기본값: heygen)
VIDEO_PROVIDER = os.getenv("VIDEO_PROVIDER", "heygen").lower()

# 전역 비디오 서비스 인스턴스 (싱글톤 패턴)
_video_service_instance = None


def get_video_service():
    """비디오 생성 서비스 인스턴스를 싱글톤으로 관리"""
    global _video_service_instance

    if _video_service_instance is None:
        try:
            _video_service_instance = VideoGenerationService(provider=VIDEO_PROVIDER)
            logger.info(f"비디오 서비스 초기화 완료: {VIDEO_PROVIDER}")
        except Exception as e:
            logger.error(f"비디오 서비스 초기화 실패: {str(e)}")
            raise HTTPException(
                status_code=503, detail=f"비디오 서비스 초기화 실패: {str(e)}"
            )

    return _video_service_instance


class VideoGenerationRequest(BaseModel):
    """비디오 생성 요청 모델 (개선된 버전)"""

    # HeyGen 파라미터
    avatar_id: Optional[str] = Field(default="default", description="HeyGen 아바타 ID")
    voice_id: Optional[str] = Field(
        default="f8c69e517f424cafaecde32dde57096b",
        description="HeyGen 음성 ID (기본: Allison)",
    )
    background: Optional[str] = Field(
        default="professional", description="HeyGen 배경 설정"
    )

    # AIStudios 파라미터
    model_id: Optional[str] = Field(default="default", description="AIStudios 모델 ID")
    cloth_id: Optional[str] = Field(
        default="BG00002320", description="AIStudios 의상 ID"
    )
    background_color: Optional[str] = Field(
        default="#ffffff", description="AIStudios 배경색"
    )
    language: Optional[str] = Field(default="ko", description="AIStudios 언어")

    class Config:
        schema_extra = {
            "example": {
                "avatar_id": "default",
                "voice_id": "f8c69e517f424cafaecde32dde57096b",
                "background": "professional",
                "model_id": "default",
                "cloth_id": "BG00002320",
                "background_color": "#ffffff",
                "language": "ko",
            }
        }


@router.post("/generate/{user_id}")
async def generate_personalized_insight(
    user_id: str,
    refresh_data: bool = Query(default=False, description="데이터 새로고침 여부"),
) -> Dict[str, Any]:
    """개인화된 AI 투자 인사이트 생성"""
    try:
        logger.info(
            f"사용자 {user_id}의 인사이트 생성 시작 (refresh_data={refresh_data})"
        )

        insight_result = insight_generator.generate_comprehensive_insight(
            user_id=user_id, refresh_data=refresh_data
        )

        if not insight_result:
            logger.warning(f"사용자 {user_id}의 인사이트 생성 실패")
            raise HTTPException(status_code=404, detail="인사이트 생성 실패")

        logger.info(f"사용자 {user_id}의 인사이트 생성 완료")

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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"인사이트 생성 중 오류 발생 (user_id={user_id}): {str(e)}")
        raise HTTPException(status_code=500, detail=f"인사이트 생성 실패: {str(e)}")


@router.post("/generate-video/{user_id}")
async def generate_insight_video(
    user_id: str,
    video_request: VideoGenerationRequest,
    refresh_data: bool = Query(default=False, description="데이터 새로고침 여부"),
) -> Dict[str, Any]:
    """개인화된 AI 투자 인사이트 영상 생성 (HeyGen 또는 AIStudios)"""
    try:
        logger.info(f"사용자 {user_id}의 인사이트 영상 생성 시작")

        # 1. 먼저 인사이트 스크립트 생성
        insight_result = insight_generator.generate_comprehensive_insight(
            user_id=user_id, refresh_data=refresh_data
        )

        if not insight_result or not insight_result.get("script"):
            logger.error(f"사용자 {user_id}의 인사이트 스크립트 생성 실패")
            raise HTTPException(status_code=404, detail="인사이트 스크립트 생성 실패")

        script = insight_result.get("script")
        logger.info(f"스크립트 생성 완료 (길이: {len(script)}자)")

        # 2. 비디오 생성 서비스 초기화
        video_service = get_video_service()

        if not video_service.is_available():
            logger.error(f"{video_service.get_provider()} 서비스 사용 불가")
            raise HTTPException(
                status_code=503,
                detail=f"{video_service.get_provider()} 서비스를 사용할 수 없습니다. API 키를 확인하세요.",
            )

        logger.info(f"비디오 생성 제공자: {video_service.get_provider()}")

        # 3. 제공자별 파라미터 준비
        if video_service.get_provider() == "heygen":
            video_params = {
                "avatar_id": video_request.avatar_id,
                "voice_id": video_request.voice_id,
                "background": video_request.background,
            }
            logger.info(
                f"HeyGen 파라미터: avatar={video_request.avatar_id}, voice={video_request.voice_id}, bg={video_request.background}"
            )
        else:  # aistudios
            video_params = {
                "model_id": video_request.model_id,
                "cloth_id": video_request.cloth_id,
                "background_color": video_request.background_color,
                "language": video_request.language,
            }
            logger.info(
                f"AIStudios 파라미터: model={video_request.model_id}, cloth={video_request.cloth_id}"
            )

        # 4. 영상 생성
        video_result = await video_service.create_video(script=script, **video_params)

        if not video_result.get("success"):
            error_details = video_result.get("details", "")
            error_msg = video_result.get("error", "알 수 없는 오류")
            logger.error(f"{video_service.get_provider()} 영상 생성 실패: {error_msg}")
            raise HTTPException(
                status_code=502,
                detail=f"{video_service.get_provider()} 영상 생성 실패: {error_msg}\n상세: {error_details}",
            )

        # 5. 제공자별 응답 형식 통일
        if video_service.get_provider() == "heygen":
            video_id = video_result.get("video_id")
            response_data = {
                "used_avatar_id": video_params["avatar_id"],
                "used_voice_id": video_params["voice_id"],
                "used_background": video_params["background"],
            }
        else:  # aistudios
            video_id = video_result.get("project_id")
            response_data = {
                "used_model_id": video_params["model_id"],
                "used_cloth_id": video_params["cloth_id"],
                "used_background_color": video_params["background_color"],
                "used_language": video_params["language"],
            }

        logger.info(f"영상 생성 요청 완료: video_id={video_id}")

        return {
            "user_id": user_id,
            "video_info": {
                "video_id": video_id,
                "video_url": video_result.get("video_url"),
                "status": video_result.get("status"),
                "provider": video_service.get_provider(),
                **response_data,
            },
            "script_info": {
                "script": script,
                "script_length": insight_result.get("script_length"),
                "estimated_reading_time": insight_result.get("estimated_reading_time"),
            },
            "insight_data": {
                "analysis_method": insight_result.get("analysis_method"),
                "token_usage": insight_result.get("token_usage"),
                "model_used": insight_result.get("model_used"),
                "data_sources": insight_result.get("data_sources"),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"영상 생성 전체 오류 (user_id={user_id}): {str(e)}")
        raise HTTPException(status_code=500, detail=f"영상 생성 실패: {str(e)}")


@router.get("/video-status/{video_id}")
async def get_video_status(video_id: str) -> Dict[str, Any]:
    """영상 생성 상태 확인 (제공자 자동 감지)"""
    try:
        video_service = get_video_service()

        if not video_service.is_available():
            raise HTTPException(
                status_code=503,
                detail=f"{video_service.get_provider()} 서비스를 사용할 수 없습니다.",
            )

        status_result = await video_service.get_video_status(video_id)

        if not status_result.get("success"):
            error_msg = status_result.get("error", "알 수 없는 오류")
            logger.error(f"비디오 상태 확인 실패 (video_id={video_id}): {error_msg}")
            raise HTTPException(status_code=500, detail=f"상태 확인 실패: {error_msg}")

        # 통일된 응답 형식
        return {
            "video_id": video_id,
            "status": status_result.get("status"),
            "video_url": status_result.get("video_url"),
            "progress": status_result.get("progress", 0),
            "provider": video_service.get_provider(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"상태 확인 중 오류 (video_id={video_id}): {str(e)}")
        raise HTTPException(status_code=500, detail=f"상태 확인 실패: {str(e)}")


@router.post("/script-to-video")
async def convert_script_to_video(
    script: str, video_request: VideoGenerationRequest
) -> Dict[str, Any]:
    """기존 스크립트를 영상으로 변환"""
    try:
        if not script or len(script.strip()) == 0:
            raise HTTPException(status_code=400, detail="스크립트가 비어있습니다")

        logger.info(f"스크립트→영상 변환 시작 (길이: {len(script)}자)")

        video_service = get_video_service()

        if not video_service.is_available():
            raise HTTPException(
                status_code=503,
                detail=f"{video_service.get_provider()} 서비스를 사용할 수 없습니다.",
            )

        # 제공자별 파라미터 준비
        if video_service.get_provider() == "heygen":
            video_params = {
                "avatar_id": video_request.avatar_id,
                "voice_id": video_request.voice_id,
                "background": video_request.background,
            }
        else:  # aistudios
            video_params = {
                "model_id": video_request.model_id,
                "cloth_id": video_request.cloth_id,
                "background_color": video_request.background_color,
                "language": video_request.language,
            }

        video_result = await video_service.create_video(script=script, **video_params)

        if not video_result.get("success"):
            error_msg = video_result.get("error", "알 수 없는 오류")
            logger.error(f"스크립트→영상 변환 실패: {error_msg}")
            raise HTTPException(
                status_code=500,
                detail=f"영상 생성 실패: {error_msg}",
            )

        # 제공자별 비디오 ID 처리
        if video_service.get_provider() == "heygen":
            video_id = video_result.get("video_id")
        else:  # aistudios
            video_id = video_result.get("project_id")

        logger.info(f"스크립트→영상 변환 완료: video_id={video_id}")

        return {
            "script": script,
            "video_info": {
                "video_id": video_id,
                "video_url": video_result.get("video_url"),
                "status": video_result.get("status"),
                "provider": video_service.get_provider(),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"스크립트→영상 변환 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"영상 생성 실패: {str(e)}")


@router.get("/video-progress/{video_id}")
async def stream_video_progress(video_id: str):
    """실시간 영상 생성 진행상황 스트리밍 (제공자별 처리)"""

    async def generate_progress():
        video_service = get_video_service()
        provider = video_service.get_provider()

        max_attempts = 120  # 최대 10분 (5초 간격)
        attempt = 0

        logger.info(
            f"영상 진행상황 스트리밍 시작: video_id={video_id}, provider={provider}"
        )

        while attempt < max_attempts:
            try:
                attempt += 1
                status_result = await video_service.get_video_status(video_id)

                if status_result.get("success"):
                    status = status_result.get("status", "unknown")
                    progress = status_result.get("progress", 0)

                    # 클라이언트에게 진행상황 전송
                    progress_data = {
                        "video_id": video_id,
                        "status": status,
                        "progress": progress,
                        "attempt": attempt,
                        "max_attempts": max_attempts,
                        "provider": provider,
                        "estimated_completion": (
                            f"{max_attempts - attempt}분 남음"
                            if status in ["processing", "waiting", "pending"]
                            else "완료"
                        ),
                    }

                    if status.lower() in ["completed", "complete"]:
                        progress_data["video_url"] = status_result.get("video_url")
                        logger.info(f"영상 생성 완료: video_id={video_id}")
                        yield f"data: {json.dumps(progress_data, ensure_ascii=False)}\n\n"
                        break
                    elif status.lower() in ["failed", "fail", "error"]:
                        progress_data["error"] = status_result.get(
                            "error", "영상 생성 실패"
                        )
                        logger.error(
                            f"영상 생성 실패: video_id={video_id}, error={progress_data['error']}"
                        )
                        yield f"data: {json.dumps(progress_data, ensure_ascii=False)}\n\n"
                        break
                    else:
                        # 진행 중
                        if attempt % 10 == 0:  # 50초마다 로그
                            logger.info(
                                f"영상 생성 진행 중: video_id={video_id}, status={status}, progress={progress}%"
                            )
                        yield f"data: {json.dumps(progress_data, ensure_ascii=False)}\n\n"
                else:
                    error_data = {
                        "video_id": video_id,
                        "status": "error",
                        "error": status_result.get("error", "상태 확인 실패"),
                        "provider": provider,
                        "attempt": attempt,
                    }
                    logger.error(
                        f"상태 확인 실패: video_id={video_id}, error={error_data['error']}"
                    )
                    yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
                    break

                await asyncio.sleep(5)  # 5초 대기

            except Exception as e:
                error_data = {
                    "video_id": video_id,
                    "status": "error",
                    "error": str(e),
                    "provider": provider,
                    "attempt": attempt,
                }
                logger.error(
                    f"진행상황 스트리밍 중 오류: video_id={video_id}, error={str(e)}"
                )
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
                break

        # 최대 시도 횟수 초과
        if attempt >= max_attempts:
            timeout_data = {
                "video_id": video_id,
                "status": "timeout",
                "error": "최대 대기 시간을 초과했습니다",
                "provider": provider,
            }
            logger.warning(f"영상 생성 타임아웃: video_id={video_id}")
            yield f"data: {json.dumps(timeout_data, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate_progress(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        },
    )


@router.get("/video-providers")
async def get_video_providers() -> Dict[str, Any]:
    """사용 가능한 비디오 제공자 목록"""
    heygen_available = False
    aistudios_available = False

    try:
        # HeyGen 서비스 체크 (import 경로 수정)
        from app.services.external.heygen_service import HeyGenService

        heygen_service = HeyGenService()
        heygen_available = heygen_service.is_available()
    except ImportError:
        logger.warning("HeyGen 서비스를 import할 수 없습니다")
    except Exception as e:
        logger.error(f"HeyGen 서비스 체크 실패: {str(e)}")

    try:
        aistudios_service = VideoGenerationService("aistudios")
        aistudios_available = aistudios_service.is_available()
    except Exception as e:
        logger.error(f"AIStudios 서비스 체크 실패: {str(e)}")

    return {
        "current_provider": VIDEO_PROVIDER,
        "providers": {
            "heygen": {
                "name": "HeyGen",
                "available": heygen_available,
                "description": "AI 아바타 기반 영상 생성",
            },
            "aistudios": {
                "name": "AI Studios",
                "available": aistudios_available,
                "description": "DeepBrain AI 기반 영상 생성",
            },
        },
    }


@router.get("/video-models")
async def get_video_models() -> Dict[str, Any]:
    """현재 제공자의 사용 가능한 모델/아바타 목록"""
    try:
        video_service = get_video_service()
        provider = video_service.get_provider()

        if provider == "heygen":
            # HeyGen 아바타 목록
            try:
                avatars = await video_service.service.get_avatars()
                return {
                    "provider": provider,
                    "models": (
                        avatars.get("avatars", []) if avatars.get("success") else []
                    ),
                    "type": "avatars",
                }
            except Exception as e:
                logger.error(f"HeyGen 아바타 목록 조회 실패: {str(e)}")
                return {
                    "provider": provider,
                    "models": [],
                    "error": "아바타 목록을 가져올 수 없습니다",
                }

        elif provider == "aistudios":
            # AIStudios 모델 목록
            try:
                models = await video_service.service.get_models()
                return {
                    "provider": provider,
                    "models": models.get("models", []) if models.get("success") else [],
                    "type": "models",
                }
            except Exception as e:
                logger.error(f"AIStudios 모델 목록 조회 실패: {str(e)}")
                return {
                    "provider": provider,
                    "models": [],
                    "error": "모델 목록을 가져올 수 없습니다",
                }

    except Exception as e:
        logger.error(f"모델 목록 조회 중 오류: {str(e)}")
        return {"error": f"모델 목록 조회 실패: {str(e)}"}


@router.get("/video-voices")
async def get_video_voices() -> Dict[str, Any]:
    """현재 제공자의 사용 가능한 음성 목록"""
    try:
        video_service = get_video_service()
        provider = video_service.get_provider()

        if provider == "heygen":
            # HeyGen 음성 목록
            try:
                voices = await video_service.service.get_voices()
                return {
                    "provider": provider,
                    "voices": voices.get("voices", []) if voices.get("success") else [],
                    "type": "voices",
                }
            except Exception as e:
                logger.error(f"HeyGen 음성 목록 조회 실패: {str(e)}")
                return {
                    "provider": provider,
                    "voices": [],
                    "error": "음성 목록을 가져올 수 없습니다",
                }

        elif provider == "aistudios":
            # AIStudios 언어 목록
            try:
                languages = await video_service.service.get_languages()
                return {
                    "provider": provider,
                    "voices": (
                        languages.get("languages", {})
                        if languages.get("success")
                        else {}
                    ),
                    "type": "languages",
                }
            except Exception as e:
                logger.error(f"AIStudios 언어 목록 조회 실패: {str(e)}")
                return {
                    "provider": provider,
                    "voices": {},
                    "error": "언어 목록을 가져올 수 없습니다",
                }

    except Exception as e:
        logger.error(f"음성 목록 조회 중 오류: {str(e)}")
        return {"error": f"음성 목록 조회 실패: {str(e)}"}


@router.post("/test-video-service")
async def test_video_service() -> Dict[str, Any]:
    """현재 비디오 서비스 연결 테스트"""
    try:
        video_service = get_video_service()
        provider = video_service.get_provider()

        if not video_service.is_available():
            return {
                "success": False,
                "provider": provider,
                "error": f"{provider} 서비스를 사용할 수 없습니다. API 키를 확인하세요.",
            }

        # 연결 테스트
        if hasattr(video_service.service, "test_connection"):
            connection_test = await video_service.service.test_connection()
            return {
                "success": connection_test,
                "provider": provider,
                "message": f"{provider} 연결 테스트 {'성공' if connection_test else '실패'}",
            }
        else:
            return {
                "success": True,
                "provider": provider,
                "message": f"{provider} 서비스가 사용 가능합니다",
            }

    except Exception as e:
        logger.error(f"비디오 서비스 테스트 실패: {str(e)}")
        return {"success": False, "error": f"서비스 테스트 실패: {str(e)}"}


@router.post("/webhook/video")
async def video_webhook(request: Request) -> Dict[str, str]:
    """비디오 제공자 웹훅 수신 엔드포인트"""
    try:
        webhook_data = await request.json()
        provider = webhook_data.get("provider", VIDEO_PROVIDER)

        logger.info(f"비디오 웹훅 수신 ({provider}): {webhook_data}")

        if provider == "heygen":
            # HeyGen 웹훅 처리
            event_type = webhook_data.get("event_type")
            event_data = webhook_data.get("event_data", {})

            if event_type == "avatar_video.success":
                video_id = event_data.get("video_id")
                video_url = event_data.get("url")
                logger.info(f"HeyGen 영상 생성 성공: {video_id}, URL: {video_url}")
            elif event_type == "avatar_video.fail":
                video_id = event_data.get("video_id")
                error_msg = event_data.get("msg")
                logger.error(f"HeyGen 영상 생성 실패: {video_id}, 오류: {error_msg}")

        elif provider == "aistudios":
            # AIStudios 웹훅 처리
            project_id = webhook_data.get("projectId")
            status = webhook_data.get("status")

            if status == "complete":
                video_url = webhook_data.get("video_url")
                logger.info(f"AIStudios 영상 생성 성공: {project_id}, URL: {video_url}")
            elif status == "fail":
                error_msg = webhook_data.get("error")
                logger.error(
                    f"AIStudios 영상 생성 실패: {project_id}, 오류: {error_msg}"
                )

        return {"status": "success", "message": "웹훅 수신 완료"}

    except Exception as e:
        logger.error(f"웹훅 처리 오류: {str(e)}")
        return {"status": "error", "message": str(e)}


# 기존 라우트들 (포트폴리오, 그래프 분석 등) - 로깅 개선
@router.get("/portfolio-analysis/{user_id}")
async def get_portfolio_analysis(user_id: str) -> Dict[str, Any]:
    """사용자 포트폴리오 분석"""
    try:
        logger.info(f"포트폴리오 분석 시작: user_id={user_id}")

        financial_data = data_collector.collect_all_data(user_id=user_id)
        user_profile = data_collector.get_personalized_data(user_id)

        portfolio_analysis = insight_generator._analyze_portfolio_performance(
            user_profile, financial_data
        )

        logger.info(f"포트폴리오 분석 완료: user_id={user_id}")

        return {
            "user_id": user_id,
            "portfolio_analysis": portfolio_analysis,
            "analyzed_at": financial_data.get("collected_at"),
        }

    except Exception as e:
        logger.error(f"포트폴리오 분석 실패 (user_id={user_id}): {str(e)}")
        raise HTTPException(status_code=500, detail=f"포트폴리오 분석 실패: {str(e)}")


@router.get("/graph-analysis")
async def get_graph_rag_analysis(
    user_id: Optional[str] = Query(default=None, description="사용자 ID (선택사항)")
) -> Dict[str, Any]:
    """Graph RAG 시장 분석"""
    try:
        logger.info(f"Graph RAG 시장 분석 시작: user_id={user_id}")

        financial_data = data_collector.collect_all_data(user_id=user_id)
        market_narrative = await enhanced_graph_rag.get_real_time_graph_context(
            f"시장 전반 분석 및 투자 인사이트"
        )

        logger.info(f"Graph RAG 시장 분석 완료: user_id={user_id}")

        return {
            "market_analysis": market_narrative,
            "analyzed_at": financial_data.get("collected_at"),
            "data_sources": financial_data.get("data_sources"),
        }

    except Exception as e:
        logger.error(f"Graph RAG 분석 실패 (user_id={user_id}): {str(e)}")
        raise HTTPException(status_code=500, detail=f"Graph RAG 분석 실패: {str(e)}")


@router.get("/news-insights")
async def get_personalized_news_insights(
    user_id: str, limit: int = Query(default=10, ge=1, le=50, description="뉴스 개수")
) -> Dict[str, Any]:
    """개인화된 뉴스 인사이트"""
    try:
        logger.info(
            f"개인화된 뉴스 인사이트 생성 시작: user_id={user_id}, limit={limit}"
        )

        financial_data = data_collector.collect_all_data(user_id=user_id)
        user_profile = data_collector.get_personalized_data(user_id)

        personalized_news = insight_generator._filter_personalized_news(
            financial_data, user_profile
        )

        logger.info(
            f"개인화된 뉴스 인사이트 생성 완료: user_id={user_id}, 필터링된 뉴스 수={len(personalized_news)}"
        )

        return {
            "user_id": user_id,
            "personalized_news": personalized_news[:limit],
            "total_news_count": len(financial_data.get("news", [])),
            "filtered_count": len(personalized_news),
        }

    except Exception as e:
        logger.error(f"뉴스 인사이트 생성 실패 (user_id={user_id}): {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"뉴스 인사이트 생성 실패: {str(e)}"
        )


@router.get("/disclosure-analysis/{user_id}")
async def get_disclosure_analysis(user_id: str) -> Dict[str, Any]:
    """사용자 맞춤 공시 분석"""
    try:
        logger.info(f"공시 분석 시작: user_id={user_id}")

        financial_data = data_collector.collect_all_data(user_id=user_id)
        user_profile = data_collector.get_personalized_data(user_id)

        portfolio_symbols = set()
        if user_profile.get("portfolio"):
            portfolio_symbols = {holding[0] for holding in user_profile["portfolio"]}

        disclosure_analysis = insight_generator._analyze_disclosure_for_portfolio(
            financial_data.get("disclosures", []), portfolio_symbols
        )

        cross_analysis = insight_generator._analyze_disclosure_news_correlation(
            financial_data.get("disclosures", []), financial_data.get("news", [])
        )

        logger.info(
            f"공시 분석 완료: user_id={user_id}, 포트폴리오 종목 수={len(portfolio_symbols)}"
        )

        return {
            "user_id": user_id,
            "disclosure_analysis": disclosure_analysis,
            "cross_analysis": cross_analysis,
            "portfolio_symbols": list(portfolio_symbols),
            "total_disclosures": len(financial_data.get("disclosures", [])),
        }

    except Exception as e:
        logger.error(f"공시 분석 실패 (user_id={user_id}): {str(e)}")
        raise HTTPException(status_code=500, detail=f"공시 분석 실패: {str(e)}")


@router.get("/debug/env")
async def debug_environment() -> Dict[str, Any]:
    """환경변수 디버깅용"""
    return {
        "video_provider": VIDEO_PROVIDER,
        "heygen_api_key_exists": bool(os.getenv("HEYGEN_API_KEY")),
        "aistudios_api_key_exists": bool(os.getenv("AISTUDIOS_API_KEY")),
        "hyperclova_api_key_exists": bool(os.getenv("NAVER_CLOVA_API_KEY")),
        "openai_api_key_exists": bool(os.getenv("OPENAI_API_KEY")),
    }


@router.get("/test")
async def test_insight_generation() -> Dict[str, Any]:
    """인사이트 생성 기능 테스트"""
    try:
        logger.info("인사이트 생성 기능 테스트 시작")

        test_data = {
            "news": [],
            "disclosures": [],
            "stock_data": [],
            "personalized": {"portfolio": [], "preferences": {}},
        }

        narrative = await enhanced_graph_rag.get_real_time_graph_context(
            "테스트 시장 분석"
        )

        logger.info("인사이트 생성 기능 테스트 완료")

        return {
            "status": "success",
            "message": "인사이트 생성 테스트 완료",
            "graph_rag_result": narrative.get("analysis", "") if narrative else None,
        }

    except Exception as e:
        logger.error(f"인사이트 생성 테스트 실패: {str(e)}")
        return {"status": "error", "message": f"테스트 실패: {str(e)}"}


# === 추가된 편의 엔드포인트들 ===


@router.get("/video-backgrounds")
async def get_video_backgrounds() -> Dict[str, Any]:
    """HeyGen에서 사용 가능한 배경 옵션들"""
    try:
        video_service = get_video_service()

        if video_service.get_provider() == "heygen":
            # HeyGen 서비스에서 배경 목록 가져오기
            if hasattr(video_service.service, "get_available_backgrounds"):
                backgrounds = video_service.service.get_available_backgrounds()
                return {
                    "provider": "heygen",
                    "backgrounds": backgrounds,
                    "categories": {
                        "basic": ["white", "black", "gray", "dark_gray"],
                        "colorful": [
                            "blue",
                            "navy",
                            "green",
                            "purple",
                            "red",
                            "orange",
                            "yellow",
                            "pink",
                        ],
                        "gradient": [
                            "gradient_blue",
                            "gradient_purple",
                            "gradient_green",
                            "gradient_orange",
                        ],
                        "business": ["office", "corporate", "professional", "meeting"],
                        "special": [
                            "greenscreen",
                            "bluescreen",
                            "studio",
                            "minimal",
                            "warm",
                            "cool",
                            "elegant",
                        ],
                    },
                }
            else:
                return {
                    "provider": "heygen",
                    "backgrounds": ["white", "professional", "office", "greenscreen"],
                    "message": "기본 배경 목록",
                }
        else:
            return {
                "provider": video_service.get_provider(),
                "message": f"{video_service.get_provider()}는 배경 옵션이 제한적입니다",
            }

    except Exception as e:
        logger.error(f"배경 목록 조회 실패: {str(e)}")
        return {"error": f"배경 목록 조회 실패: {str(e)}"}


@router.post("/quick-video")
async def create_quick_video(
    script: str = Query(..., description="영상 스크립트"),
    background: str = Query(default="professional", description="배경 설정"),
    voice_type: str = Query(
        default="allison", description="음성 타입 (allison/korean)"
    ),
) -> Dict[str, Any]:
    """빠른 영상 생성 (기본 설정 사용)"""
    try:
        if not script or len(script.strip()) == 0:
            raise HTTPException(status_code=400, detail="스크립트가 비어있습니다")

        logger.info(
            f"빠른 영상 생성 시작: voice_type={voice_type}, background={background}"
        )

        video_service = get_video_service()

        if not video_service.is_available():
            raise HTTPException(
                status_code=503,
                detail=f"{video_service.get_provider()} 서비스를 사용할 수 없습니다.",
            )

        # 음성 타입에 따른 voice_id 선택
        if voice_type.lower() == "allison":
            voice_id = "f8c69e517f424cafaecde32dde57096b"  # Allison
        elif voice_type.lower() == "korean":
            voice_id = "bef4755ca1f442359c2fe6420690c8f7"  # InJoon
        else:
            voice_id = "f8c69e517f424cafaecde32dde57096b"  # 기본값: Allison

        if video_service.get_provider() == "heygen":
            video_result = await video_service.create_video(
                script=script,
                avatar_id="default",
                voice_id=voice_id,
                background=background,
            )
        else:
            # AIStudios는 기본 설정으로
            video_result = await video_service.create_video(
                script=script,
                model_id="default",
                language="ko" if voice_type.lower() == "korean" else "en",
            )

        if not video_result.get("success"):
            error_msg = video_result.get("error", "알 수 없는 오류")
            raise HTTPException(status_code=500, detail=f"영상 생성 실패: {error_msg}")

        video_id = video_result.get("video_id") or video_result.get("project_id")

        logger.info(f"빠른 영상 생성 완료: video_id={video_id}")

        return {
            "video_id": video_id,
            "video_url": video_result.get("video_url"),
            "status": video_result.get("status"),
            "provider": video_service.get_provider(),
            "settings_used": {
                "voice_type": voice_type,
                "background": background,
                "script_length": len(script),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"빠른 영상 생성 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"빠른 영상 생성 실패: {str(e)}")


@router.get("/video-presets")
async def get_video_presets() -> Dict[str, Any]:
    """미리 정의된 영상 생성 프리셋들"""
    return {
        "presets": {
            "professional_presentation": {
                "name": "전문적인 프레젠테이션",
                "avatar_id": "default",
                "voice_id": "f8c69e517f424cafaecde32dde57096b",  # Allison
                "background": "professional",
                "description": "비즈니스 프레젠테이션에 적합",
            },
            "korean_news": {
                "name": "한국어 뉴스 스타일",
                "avatar_id": "default",
                "voice_id": "bef4755ca1f442359c2fe6420690c8f7",  # InJoon
                "background": "corporate",
                "description": "한국어 뉴스 브리핑 스타일",
            },
            "colorful_marketing": {
                "name": "컬러풀 마케팅",
                "avatar_id": "default",
                "voice_id": "f8c69e517f424cafaecde32dde57096b",  # Allison
                "background": "gradient_blue",
                "description": "활발한 마케팅 영상",
            },
            "minimal_education": {
                "name": "미니멀 교육",
                "avatar_id": "default",
                "voice_id": "f8c69e517f424cafaecde32dde57096b",  # Allison
                "background": "minimal",
                "description": "깔끔한 교육 콘텐츠",
            },
            "greenscreen_custom": {
                "name": "그린스크린 (커스텀 배경용)",
                "avatar_id": "default",
                "voice_id": "f8c69e517f424cafaecde32dde57096b",  # Allison
                "background": "greenscreen",
                "description": "후편집으로 배경 교체 가능",
            },
        }
    }


@router.post("/video-from-preset")
async def create_video_from_preset(
    script: str,
    preset_name: str = Query(..., description="프리셋 이름"),
) -> Dict[str, Any]:
    """프리셋을 사용한 영상 생성"""
    try:
        if not script or len(script.strip()) == 0:
            raise HTTPException(status_code=400, detail="스크립트가 비어있습니다")

        # 프리셋 정보 가져오기
        presets_response = await get_video_presets()
        presets = presets_response.get("presets", {})

        if preset_name not in presets:
            available_presets = list(presets.keys())
            raise HTTPException(
                status_code=400,
                detail=f"존재하지 않는 프리셋: {preset_name}. 사용 가능한 프리셋: {available_presets}",
            )

        preset = presets[preset_name]
        logger.info(f"프리셋 영상 생성 시작: preset={preset_name}")

        video_service = get_video_service()

        if not video_service.is_available():
            raise HTTPException(
                status_code=503,
                detail=f"{video_service.get_provider()} 서비스를 사용할 수 없습니다.",
            )

        # 프리셋 설정으로 영상 생성
        if video_service.get_provider() == "heygen":
            video_result = await video_service.create_video(
                script=script,
                avatar_id=preset["avatar_id"],
                voice_id=preset["voice_id"],
                background=preset["background"],
            )
        else:
            # AIStudios는 기본 설정으로
            video_result = await video_service.create_video(
                script=script,
                model_id="default",
                language="ko" if "korean" in preset_name.lower() else "en",
            )

        if not video_result.get("success"):
            error_msg = video_result.get("error", "알 수 없는 오류")
            raise HTTPException(status_code=500, detail=f"영상 생성 실패: {error_msg}")

        video_id = video_result.get("video_id") or video_result.get("project_id")

        logger.info(f"프리셋 영상 생성 완료: preset={preset_name}, video_id={video_id}")

        return {
            "video_id": video_id,
            "video_url": video_result.get("video_url"),
            "status": video_result.get("status"),
            "provider": video_service.get_provider(),
            "preset_used": {
                "name": preset_name,
                "description": preset["description"],
                **preset,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"프리셋 영상 생성 실패 (preset={preset_name}): {str(e)}")
        raise HTTPException(status_code=500, detail=f"프리셋 영상 생성 실패: {str(e)}")
