# app/services/heygen_service.py (voice_id 기본값 처리 수정)
import httpx
import asyncio
import os
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


class HeyGenService:
    # 음성 ID 상수들 (클래스 레벨로 이동)
    ALLISON_VOICE_ID = "f8c69e517f424cafaecde32dde57096b"  # Allison - English Female
    INJOON_VOICE_ID = "bef4755ca1f442359c2fe6420690c8f7"   # InJoon - Korean Male

    def __init__(self):
        self.api_key = os.getenv("HEYGEN_API_KEY")
        self.base_url = "https://api.heygen.com/v2"
        self._default_avatars = []
        self._default_voices = []

        if not self.api_key:
            raise ValueError(
                "HEYGEN_API_KEY가 환경변수에 설정되지 않았습니다. .env 파일을 확인하세요."
            )

    def is_available(self) -> bool:
        """HeyGen 서비스 사용 가능 여부 확인"""
        return bool(self.api_key)

    async def test_connection(self) -> bool:
        """HeyGen API 연결 테스트"""
        try:
            if not self.is_available():
                return False

            # 아바타 목록 조회로 연결 테스트
            avatars_result = await self.get_avatars()
            return avatars_result.get("success", False)

        except Exception as e:
            logger.error(f"HeyGen 연결 테스트 실패: {str(e)}")
            return False

    async def _get_default_avatar(self) -> str:
        """사용 가능한 첫 번째 아바타 ID 반환"""
        if not self._default_avatars:
            avatars_response = await self.get_avatars()
            if avatars_response.get("success", True) and avatars_response.get(
                "avatars"
            ):
                self._default_avatars = avatars_response.get("avatars", [])
            elif avatars_response.get("data") and avatars_response["data"].get(
                "avatars"
            ):
                self._default_avatars = avatars_response["data"]["avatars"]

        if self._default_avatars:
            return self._default_avatars[0].get("avatar_id", "")
        return "Amy_sitting_sofa_side"  # 확실히 존재하는 아바타 ID로 폴백

    async def _get_default_voice(self) -> str:
        """기본 음성 ID 반환 (Allison)"""
        return self.ALLISON_VOICE_ID

    def _resolve_voice_id(self, voice_id: str) -> str:
        """
        voice_id 파라미터를 실제 음성 ID로 변환
        """
        if voice_id == "default" or voice_id is None or voice_id == "":
            return self.ALLISON_VOICE_ID
        elif voice_id.lower() == "allison":
            return self.ALLISON_VOICE_ID
        elif voice_id.lower() == "korean" or voice_id.lower() == "injoon":
            return self.INJOON_VOICE_ID
        else:
            # 이미 실제 voice_id인 경우 그대로 반환
            return voice_id

    def _get_background_config(self, background: str) -> Dict:
        """
        배경 설정을 HeyGen API 형식으로 변환 (대폭 확장)
        """
        # 프리셋 배경들
        background_presets = {
            # 단색 배경들
            "white": {"type": "color", "value": "#FFFFFF"},
            "black": {"type": "color", "value": "#000000"},
            "gray": {"type": "color", "value": "#F5F5F5"},
            "dark_gray": {"type": "color", "value": "#2C2C2C"},
            "blue": {"type": "color", "value": "#4A90E2"},
            "navy": {"type": "color", "value": "#1E3A8A"},
            "green": {"type": "color", "value": "#10B981"},
            "purple": {"type": "color", "value": "#8B5CF6"},
            "red": {"type": "color", "value": "#EF4444"},
            "orange": {"type": "color", "value": "#F97316"},
            "yellow": {"type": "color", "value": "#EAB308"},
            "pink": {"type": "color", "value": "#EC4899"},

            # 그라데이션 느낌 (단색으로 대체)
            "gradient_blue": {"type": "color", "value": "#3B82F6"},
            "gradient_purple": {"type": "color", "value": "#A855F7"},
            "gradient_green": {"type": "color", "value": "#059669"},
            "gradient_orange": {"type": "color", "value": "#EA580C"},

            # 비즈니스/오피스 계열
            "office": {"type": "color", "value": "#F8FAFC"},
            "corporate": {"type": "color", "value": "#E2E8F0"},
            "professional": {"type": "color", "value": "#CBD5E1"},
            "meeting": {"type": "color", "value": "#94A3B8"},

            # 특수 용도
            "greenscreen": {"type": "color", "value": "#00FF00"},  # 크로마키용
            "bluescreen": {"type": "color", "value": "#0000FF"},   # 크로마키용
            "studio": {"type": "color", "value": "#1A1A1A"},      # 스튜디오 느낌
            "minimal": {"type": "color", "value": "#FAFAFA"},     # 미니멀
            "warm": {"type": "color", "value": "#FEF3C7"},        # 따뜻한 느낌
            "cool": {"type": "color", "value": "#DBEAFE"},        # 시원한 느낌
            "elegant": {"type": "color", "value": "#F3F4F6"},     # 우아한 느낌
        }

        # 프리셋에서 찾기
        if background.lower() in background_presets:
            return background_presets[background.lower()]

        # 헥스 컬러코드 직접 입력
        elif background.startswith("#"):
            return {"type": "color", "value": background}

        # 이미지 URL
        elif background.startswith("http"):
            return {"type": "image", "url": background}

        # 기본값
        else:
            logger.warning(f"알 수 없는 배경 설정: {background}, 기본값 사용")
            return {"type": "color", "value": "#FFFFFF"}

    async def create_video(
        self,
        script: str,
        avatar_id: str = "default",
        voice_id: str = "default",  # 여기서 "default" 받아서 처리
        background: str = "office",
    ) -> Dict:
        """
        HeyGen API를 사용해서 영상 생성

        Args:
            script: 영상에서 읽을 스크립트
            avatar_id: 사용할 아바타 ID
            voice_id: 사용할 음성 ID (default, allison, korean, 또는 실제 ID)
            background: 배경 설정 (프리셋 이름, 헥스코드, 이미지URL)

        Returns:
            영상 생성 결과
        """
        try:
            # 스크립트 길이 체크 (HeyGen 제한사항)
            if len(script) > 5000:
                script = script[:4900] + "..."
                logger.warning("스크립트가 너무 길어서 자동으로 축약되었습니다.")

            # voice_id 해결 (중요!)
            resolved_voice_id = self._resolve_voice_id(voice_id)
            logger.info(f"Voice ID 변환: {voice_id} -> {resolved_voice_id}")

            # 기본 아바타 처리
            if avatar_id == "default":
                avatar_id = await self._get_default_avatar()
                if not avatar_id:
                    return {
                        "success": False,
                        "error": "사용 가능한 아바타를 찾을 수 없습니다.",
                    }

            headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}

            # HeyGen API v2 형식에 맞춘 페이로드
            payload = {
                "video_inputs": [
                    {
                        "character": {
                            "type": "avatar",
                            "avatar_id": avatar_id,
                            "avatar_style": "normal",
                        },
                        "voice": {
                            "type": "text",
                            "input_text": script,
                            "voice_id": resolved_voice_id,  # 해결된 voice_id 사용
                            "speed": 1.0,
                        },
                        "background": self._get_background_config(background),
                    }
                ],
                "dimension": {"width": 1280, "height": 720},
                "aspect_ratio": "16:9",
                "test": False,  # 실제 영상 생성
            }

            logger.info(f"HeyGen 영상 생성 요청: 아바타={avatar_id}, 음성={resolved_voice_id}, 배경={background}")

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/video/generate", headers=headers, json=payload
                )

                logger.info(f"HeyGen API 응답: {response.status_code}")

                if response.status_code == 200:
                    result = response.json()
                    video_id = result.get("data", {}).get("video_id")

                    if video_id:
                        logger.info(f"영상 생성 시작됨: {video_id}")
                        return {
                            "success": True,
                            "video_id": video_id,
                            "video_url": None,  # 생성 중이므로 나중에 확인
                            "status": "processing",
                        }
                    else:
                        return {
                            "success": False,
                            "error": "영상 ID를 받지 못했습니다",
                            "details": result,
                        }
                else:
                    error_detail = await self._parse_error_response(response)
                    logger.error(
                        f"HeyGen API 오류: {response.status_code} - {error_detail}"
                    )
                    return {
                        "success": False,
                        "error": f"API 요청 실패: {response.status_code}",
                        "details": error_detail,
                    }

        except Exception as e:
            logger.error(f"HeyGen 영상 생성 오류: {str(e)}")
            return {"success": False, "error": f"영상 생성 실패: {str(e)}"}

    async def _parse_error_response(self, response: httpx.Response) -> str:
        """API 오류 응답 파싱"""
        try:
            error_data = response.json()
            error_info = error_data.get("error", {})
            return f"{error_info.get('code', 'unknown')}: {error_info.get('message', response.text)}"
        except:
            return response.text

    async def get_video_status(self, video_id: str) -> Dict:
        """영상 생성 상태 확인"""
        try:
            headers = {"X-API-KEY": self.api_key}

            # HeyGen API v1 엔드포인트 사용 (중요!)
            status_url = f"https://api.heygen.com/v1/video_status.get?video_id={video_id}"
            logger.info(f"비디오 상태 확인 URL: {status_url}")

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(status_url, headers=headers)

                logger.info(f"비디오 상태 확인 응답: {response.status_code}")

                if response.status_code == 200:
                    result = response.json()

                    # HeyGen v1 API 응답 구조
                    if result.get("code") == 100:  # 성공 코드
                        data = result.get("data", {})

                        # progress 계산 (HeyGen v1에서는 제공 안 함)
                        status = data.get("status", "unknown")
                        progress = 0
                        if status == "completed":
                            progress = 100
                        elif status == "processing":
                            progress = 50  # 임시값
                        elif status == "pending" or status == "waiting":
                            progress = 10  # 임시값

                        return {
                            "success": True,
                            "video_id": video_id,
                            "status": status,
                            "video_url": data.get("video_url"),
                            "progress": progress,
                            "duration": data.get("duration"),
                            "created_at": data.get("created_at"),
                            "thumbnail_url": data.get("thumbnail_url"),
                            "caption_url": data.get("caption_url"),
                            "gif_url": data.get("gif_url"),
                        }
                    else:
                        # API 에러 응답
                        error_msg = result.get("message", "알 수 없는 오류")
                        return {
                            "success": False,
                            "error": f"API 에러: {error_msg}",
                            "details": result
                        }
                else:
                    return {
                        "success": False,
                        "error": f"상태 확인 실패: {response.status_code}",
                        "details": response.text
                    }

        except Exception as e:
            logger.error(f"비디오 상태 확인 오류: {str(e)}")
            return {"success": False, "error": f"상태 확인 오류: {str(e)}"}

    async def _wait_for_video_completion(
        self, video_id: str, max_wait_time: int = 300
    ) -> Optional[str]:
        """
        영상 생성 완료까지 대기하고 URL 반환
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            try:
                status_result = await self.get_video_status(video_id)

                if not status_result.get("success"):
                    logger.error(f"상태 확인 실패: {status_result.get('error')}")
                    return None

                status = status_result.get("status")

                if status == "completed":
                    video_url = status_result.get("video_url")
                    logger.info(f"영상 생성 완료: {video_url}")
                    return video_url
                elif status == "failed":
                    logger.error(f"영상 생성 실패: {status_result}")
                    return None
                else:
                    # 아직 처리 중
                    progress = status_result.get("progress", 0)
                    logger.info(f"영상 생성 중... 상태: {status}, 진행률: {progress}%")

                # 최대 대기 시간 확인
                current_time = asyncio.get_event_loop().time()
                if current_time - start_time > max_wait_time:
                    logger.error(f"영상 생성 시간 초과: {max_wait_time}초")
                    return None

                # 15초 대기 후 다시 확인
                await asyncio.sleep(15)

            except Exception as e:
                logger.error(f"영상 상태 확인 오류: {str(e)}")
                await asyncio.sleep(10)

    async def get_avatars(self) -> Dict:
        """사용 가능한 아바타 목록 조회"""
        try:
            headers = {"X-API-KEY": self.api_key}

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.base_url}/avatars", headers=headers)

                if response.status_code == 200:
                    result = response.json()
                    # HeyGen API 응답 구조에 맞춰서 반환
                    return {
                        "success": True,
                        "data": result.get("data", {}),
                        "avatars": result.get("data", {}).get("avatars", []),
                    }
                else:
                    return {
                        "success": False,
                        "error": f"아바타 목록 조회 실패: {response.status_code}",
                        "details": response.text,
                    }

        except Exception as e:
            return {"success": False, "error": f"아바타 목록 조회 오류: {str(e)}"}

    async def get_voices(self) -> Dict:
        """사용 가능한 음성 목록 조회"""
        try:
            headers = {"X-API-KEY": self.api_key}

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.base_url}/voices", headers=headers)

                if response.status_code == 200:
                    result = response.json()
                    return {
                        "success": True,
                        "data": result.get("data", {}),
                        "voices": result.get("data", {}).get("voices", []),
                    }
                else:
                    return {
                        "success": False,
                        "error": f"음성 목록 조회 실패: {response.status_code}",
                        "details": response.text,
                    }

        except Exception as e:
            return {"success": False, "error": f"음성 목록 조회 오류: {str(e)}"}

    # === 편의 메서드들 ===

    async def create_video_with_allison(
        self,
        script: str,
        avatar_id: str = "default",
        background: str = "professional"
    ) -> Dict:
        """
        Allison 음성으로 영상 생성 (편의 함수)
        """
        return await self.create_video(
            script=script,
            avatar_id=avatar_id,
            voice_id=self.ALLISON_VOICE_ID,  # 직접 ID 전달
            background=background
        )

    async def create_video_with_korean(
        self,
        script: str,
        avatar_id: str = "default",
        background: str = "professional"
    ) -> Dict:
        """
        한국어 음성(InJoon)으로 영상 생성 (편의 함수)
        """
        return await self.create_video(
            script=script,
            avatar_id=avatar_id,
            voice_id=self.INJOON_VOICE_ID,  # 직접 ID 전달
            background=background
        )

    def get_available_backgrounds(self) -> List[str]:
        """
        사용 가능한 배경 프리셋 목록 반환
        """
        return [
            # 기본 단색들
            "white", "black", "gray", "dark_gray",

            # 컬러풀한 배경들
            "blue", "navy", "green", "purple", "red", "orange", "yellow", "pink",

            # 그라데이션 느낌
            "gradient_blue", "gradient_purple", "gradient_green", "gradient_orange",

            # 비즈니스/전문적
            "office", "corporate", "professional", "meeting",

            # 특수 용도
            "greenscreen", "bluescreen", "studio", "minimal", "warm", "cool", "elegant"
        ]

    async def create_video_with_custom_background(
        self,
        script: str,
        background_image_url: str,
        avatar_id: str = "default",
        voice_id: str = "default"  # 여기서도 처리됨
    ) -> Dict:
        """
        커스텀 이미지 배경으로 영상 생성
        """
        resolved_voice_id = self._resolve_voice_id(voice_id)

        if avatar_id == "default":
            avatar_id = await self._get_default_avatar()

        headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}

        payload = {
            "video_inputs": [
                {
                    "character": {
                        "type": "avatar",
                        "avatar_id": avatar_id,
                        "avatar_style": "normal",
                    },
                    "voice": {
                        "type": "text",
                        "input_text": script,
                        "voice_id": resolved_voice_id,  # 해결된 voice_id 사용
                        "speed": 1.0,
                    },
                    "background": {
                        "type": "image",
                        "url": background_image_url
                    },
                }
            ],
            "dimension": {"width": 1280, "height": 720},
            "aspect_ratio": "16:9",
            "test": False,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/video/generate", headers=headers, json=payload
                )

                if response.status_code == 200:
                    result = response.json()
                    video_id = result.get("data", {}).get("video_id")

                    if video_id:
                        return {
                            "success": True,
                            "video_id": video_id,
                            "video_url": None,
                            "status": "processing",
                        }
                    else:
                        return {
                            "success": False,
                            "error": "영상 ID를 받지 못했습니다",
                            "details": result,
                        }
                else:
                    error_detail = await self._parse_error_response(response)
                    return {
                        "success": False,
                        "error": f"API 요청 실패: {response.status_code}",
                        "details": error_detail,
                    }

        except Exception as e:
            logger.error(f"커스텀 배경 영상 생성 오류: {str(e)}")
            return {"success": False, "error": f"영상 생성 실패: {str(e)}"}

    async def list_all_voices_detailed(self) -> None:
        """
        모든 음성 목록을 자세히 출력 (디버깅용)
        """
        try:
            voices_result = await self.get_voices()
            if not voices_result.get("success", True):
                print(f"음성 목록 조회 실패: {voices_result}")
                return

            voices = voices_result.get("voices", [])
            if not voices and voices_result.get("data", {}).get("voices"):
                voices = voices_result["data"]["voices"]

            print(f"\n총 {len(voices)}개의 음성 발견:")
            print("-" * 100)

            korean_voices = []
            english_voices = []
            other_voices = []

            for voice in voices:
                voice_info = {
                    "id": voice.get("voice_id", ""),
                    "name": voice.get("name", "").strip(),  # 공백 제거
                    "language": voice.get("language", ""),
                    "gender": voice.get("gender", ""),
                    "interactive_support": voice.get("support_interactive_avatar", False),
                    "emotion_support": voice.get("emotion_support", False)
                }

                if "korean" in voice.get("language", "").lower() or "korea" in voice.get("language", "").lower():
                    korean_voices.append(voice_info)
                elif "english" in voice.get("language", "").lower():
                    english_voices.append(voice_info)
                else:
                    other_voices.append(voice_info)

            # 한국어 음성들
            if korean_voices:
                print("\n🇰🇷 한국어 음성들:")
                for voice in korean_voices:
                    if voice['id'] == self.INJOON_VOICE_ID:
                        print(f"  ⭐ {voice['name']} ({voice['id']}) <- 한국어 기본 음성!")
                    else:
                        print(f"  - {voice['name']} ({voice['id']})")

            # 영어 음성들 중 Allison 찾기
            print("\n🇺🇸 영어 음성들:")
            for voice in english_voices:
                if voice['id'] == self.ALLISON_VOICE_ID:
                    print(f"  ⭐ {voice['name']} ({voice['id']}) <- 현재 기본 음성!")
                else:
                    print(f"  - {voice['name']} ({voice['id']})")

        except Exception as e:
            print(f"음성 목록 출력 오류: {str(e)}")
