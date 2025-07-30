# app/services/aistudios_service.py
import httpx
import asyncio
import os
import logging
import uuid
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


class AIStudiosService:
    """AIStudios API 클라이언트 (DeepBrain AI) - 문서 기반 수정 버전"""

    def __init__(self):
        self.api_key = os.getenv("AISTUDIOS_API_KEY")
        # 문서에서 확인한 도메인들
        self.base_url_v2 = "https://v2.aistudios.com/api/odin"
        self.base_url_v3 = "https://app.aistudios.com/api/odin/v3"

        if not self.api_key:
            raise ValueError(
                "AISTUDIOS_API_KEY가 환경변수에 설정되지 않았습니다. .env 파일을 확인하세요."
            )

        logger.info("AIStudios 서비스 초기화 완료")

    def _get_headers(self) -> Dict[str, str]:
        """AIStudios API 요청 헤더"""
        return {"Authorization": self.api_key, "Content-Type": "application/json"}

    async def create_video_simple(
        self, script: str, model: str = "M000004017", clothes: str = "BG00006160"
    ) -> Dict:
        """
        간단한 AIStudios 영상 생성 (문서 예제 기반)

        Args:
            script: 영상 스크립트
            model: 아바타 모델 ID
            clothes: 의상 ID

        Returns:
            영상 생성 결과
        """
        try:
            # 스크립트 길이 체크
            if len(script) > 1000:
                script = script[:900] + "..."
                logger.warning("스크립트가 너무 길어서 자동으로 축약되었습니다.")

            # 문서에 나온 간단한 형식 사용
            payload = {
                "scenes": [
                    {
                        "AIModel": {
                            "script": script,
                            "model": model,
                            "clothes": clothes,
                            "locationX": -0.28,
                            "locationY": 0.19,
                            "scale": 1,
                        }
                    }
                ]
            }

            headers = self._get_headers()

            # v2 API 엔드포인트 사용 (문서 기준)
            url = f"{self.base_url_v2}/editor/project"

            logger.info(f"AIStudios 영상 생성 요청 (간단 버전): 모델={model}")
            logger.info(f"URL: {url}")
            logger.info(f"스크립트 길이: {len(script)}")

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=headers, json=payload)

                logger.info(f"AIStudios API 응답: {response.status_code}")
                logger.info(f"응답 내용: {response.text}")

                if response.status_code == 200:
                    result = response.json()
                    project_key = result.get("key")  # v2 API는 key를 반환

                    if project_key:
                        logger.info(f"영상 생성 시작됨: {project_key}")
                        return {
                            "success": True,
                            "project_id": project_key,
                            "video_url": None,
                            "status": "processing",
                            "model_used": model,
                            "clothes_used": clothes,
                        }
                    else:
                        return {
                            "success": False,
                            "error": "프로젝트 키를 받지 못했습니다",
                            "details": result,
                        }
                else:
                    error_detail = await self._parse_error_response(response)
                    logger.error(
                        f"AIStudios API 오류: {response.status_code} - {error_detail}"
                    )
                    return {
                        "success": False,
                        "error": f"API 요청 실패: {response.status_code}",
                        "details": error_detail,
                    }

        except Exception as e:
            logger.error(f"AIStudios 영상 생성 오류: {str(e)}")
            return {"success": False, "error": f"영상 생성 실패: {str(e)}"}

    async def create_video(
        self,
        script: str,
        model_id: str = "default",
        cloth_id: str = "BG00006160",
        background_color: str = "#ffffff",
        language: str = "ko",
        webhook_url: Optional[str] = None,
    ) -> Dict:
        """
        통합 인터페이스를 위한 래퍼 함수
        """
        # 기본 모델 처리
        if model_id == "default":
            model_id = "M000004017"  # 문서에서 확인한 기본 모델

        # 간단한 버전 사용
        return await self.create_video_simple(script, model_id, cloth_id)

    async def _parse_error_response(self, response: httpx.Response) -> str:
        """API 오류 응답 파싱"""
        try:
            error_data = response.json()

            # 에러 구조 분석
            if "error" in error_data:
                error_info = error_data["error"]
                if isinstance(error_info, dict):
                    code = error_info.get("code", "unknown")
                    msg = error_info.get("msg", "오류 메시지 없음")
                    return f"코드 {code}: {msg}"
                else:
                    return str(error_info)

            return f"AIStudios 오류: {error_data}"
        except:
            return response.text

    async def get_project_status(self, project_id: str) -> Dict:
        """프로젝트 상태 확인 (v2 API 기준)"""
        try:
            headers = self._get_headers()
            url = f"{self.base_url_v2}/editor/progress/{project_id}"

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                logger.info(f"상태 확인 응답: {response.status_code}")
                logger.info(f"응답 내용: {response.text}")

                if response.status_code == 200:
                    result = response.json()

                    # v2 API 응답 구조에 맞춰 처리
                    status = result.get("status", "unknown")
                    progress = result.get("progress", 0)
                    video_url = result.get("url")  # v2에서는 url 필드 사용

                    return {
                        "success": True,
                        "project_id": project_id,
                        "status": status.lower() if status else "unknown",
                        "progress": progress,
                        "video_url": video_url,
                        "created_at": result.get("created_at"),
                    }
                else:
                    error_detail = await self._parse_error_response(response)
                    return {
                        "success": False,
                        "error": f"상태 확인 실패: {response.status_code}",
                        "details": error_detail,
                    }

        except Exception as e:
            logger.error(f"프로젝트 상태 확인 오류: {str(e)}")
            return {"success": False, "error": f"상태 확인 오류: {str(e)}"}

    async def test_api_access(self) -> Dict:
        """API 접근 권한 테스트"""
        try:
            # 매우 간단한 테스트 요청
            test_script = "테스트"
            result = await self.create_video_simple(test_script)

            return {
                "success": result.get("success", False),
                "message": "API 접근 테스트 완료",
                "details": result,
            }

        except Exception as e:
            return {"success": False, "error": f"API 접근 테스트 실패: {str(e)}"}

    async def get_models(self) -> Dict:
        """사용 가능한 모델 목록 (기본값 반환)"""
        # API에서 모델 목록을 가져오는 엔드포인트가 없으므로 기본값 제공
        default_models = [
            {
                "model_id": "M000004017",
                "name": "기본 아바타 1",
                "description": "기본 제공 아바타",
            },
            {
                "model_id": "M000045058",
                "name": "기본 아바타 2",
                "description": "기본 제공 아바타",
            },
        ]

        return {"success": True, "models": default_models}

    async def get_languages(self) -> Dict:
        """지원 언어 목록 조회"""
        try:
            supported_languages = {
                "ko": "한국어",
                "en": "English",
                "ja": "日本語",
                "zh": "中文",
            }

            return {"success": True, "languages": supported_languages}

        except Exception as e:
            logger.error(f"언어 목록 조회 오류: {str(e)}")
            return {"success": False, "error": f"언어 목록 조회 오류: {str(e)}"}

    def is_available(self) -> bool:
        """AIStudios 서비스 사용 가능 여부 확인"""
        return bool(self.api_key)

    async def test_connection(self) -> bool:
        """AIStudios API 연결 테스트"""
        try:
            if not self.is_available():
                logger.error("API 키가 설정되지 않음")
                return False

            # API 접근 권한 테스트
            test_result = await self.test_api_access()
            success = test_result.get("success", False)

            if not success:
                logger.error(f"연결 테스트 실패: {test_result.get('error')}")

            return success

        except Exception as e:
            logger.error(f"AIStudios 연결 테스트 실패: {str(e)}")
            return False


class VideoGenerationService:
    """HeyGen과 AIStudios를 선택적으로 사용할 수 있는 통합 서비스"""

    def __init__(self, provider: str = "heygen"):
        """
        Args:
            provider: "heygen" 또는 "aistudios"
        """
        self.provider = provider.lower()
        self.service = None

        if self.provider == "heygen":
            try:
                from .heygen_service import HeyGenService

                self.service = HeyGenService()
                logger.info("HeyGen 서비스 초기화 완료")
            except Exception as e:
                logger.error(f"HeyGen 서비스 초기화 실패: {e}")

        elif self.provider == "aistudios":
            try:
                self.service = AIStudiosService()
                logger.info("AIStudios 서비스 초기화 완료")
            except Exception as e:
                logger.error(f"AIStudios 서비스 초기화 실패: {e}")
        else:
            raise ValueError(
                f"지원하지 않는 제공자: {provider}. 'heygen' 또는 'aistudios'를 사용하세요."
            )

    async def create_video(self, script: str, **kwargs) -> Dict:
        """통합 영상 생성 인터페이스"""
        if not self.service:
            return {
                "success": False,
                "error": f"{self.provider} 서비스가 초기화되지 않았습니다",
            }

        try:
            if self.provider == "heygen":
                # HeyGen 서비스 호출
                return await self.service.create_video(
                    script=script,
                    avatar_id=kwargs.get("avatar_id", "default"),
                    voice_id=kwargs.get("voice_id", "default"),
                    background=kwargs.get("background", "office"),
                )
            elif self.provider == "aistudios":
                # AIStudios 서비스 호출
                return await self.service.create_video(
                    script=script,
                    model_id=kwargs.get("model_id", "default"),
                    cloth_id=kwargs.get("cloth_id", "BG00006160"),
                    background_color=kwargs.get("background_color", "#ffffff"),
                    language=kwargs.get("language", "ko"),
                )
        except Exception as e:
            return {
                "success": False,
                "error": f"{self.provider} 영상 생성 실패: {str(e)}",
            }

    async def get_video_status(self, video_id: str) -> Dict:
        """통합 영상 상태 확인 인터페이스"""
        if not self.service:
            return {
                "success": False,
                "error": f"{self.provider} 서비스가 초기화되지 않았습니다",
            }

        try:
            if self.provider == "heygen":
                return await self.service.get_video_status(video_id)
            elif self.provider == "aistudios":
                return await self.service.get_project_status(video_id)
        except Exception as e:
            return {
                "success": False,
                "error": f"{self.provider} 상태 확인 실패: {str(e)}",
            }

    def get_provider(self) -> str:
        """현재 사용 중인 제공자 반환"""
        return self.provider

    def is_available(self) -> bool:
        """서비스 사용 가능 여부 확인"""
        return self.service and self.service.is_available() if self.service else False
