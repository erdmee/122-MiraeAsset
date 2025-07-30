import requests
import json
import time
from typing import Dict, List, Optional
from datetime import datetime
from app.config import settings


class HyperClovaXResponse:
    """HyperCLOVA X 응답을 담는 클래스"""

    def __init__(self, response_data: Dict):
        self.raw_data = response_data
        self.result = response_data.get("result", {})
        self.message = self.result.get("message", {})
        self.content = self.message.get("content", "")
        self.input_length = self.result.get("inputLength", 0)
        self.output_length = self.result.get("outputLength", 0)
        self.stop_reason = self.result.get("stopReason", "")
        self.ai_filter = self.result.get("aiFilter", [])

    def get_content(self) -> str:
        """생성된 텍스트 내용 반환"""
        return self.content

    def get_usage(self) -> Dict:
        """토큰 사용량 정보"""
        return {
            "total_tokens": self.input_length + self.output_length,
            "prompt_tokens": self.input_length,
            "completion_tokens": self.output_length,
        }

    def get(self, key: str, default=None):
        """dict 스타일 접근을 위한 get 메서드"""
        if key == "content":
            return self.content
        elif key == "usage":
            return self.get_usage()
        return getattr(self, key, default)


class HyperClovaXClient:
    """네이버 CLOVA Studio HyperCLOVA X API 클라이언트 (순수 HyperCLOVA 방식)"""

    def __init__(self):
        self.api_key = settings.NAVER_CLOVA_API_KEY
        self.api_host = "clovastudio.stream.ntruss.com"
        self.model = "HCX-003"
        self.base_url = f"https://{self.api_host}"

        if self.api_key:
            print(">> HyperCLOVA X API 클라이언트 초기화 완료")
            print(f">> 사용 모델: {self.model}")
        else:
            print(">> HyperCLOVA X API 키가 설정되지 않음")

    def is_available(self) -> bool:
        """API 사용 가능 여부 확인"""
        return bool(self.api_key)

    def get_current_provider(self) -> str:
        """현재 사용 중인 프로바이더 반환"""
        return f"HyperCLOVA X ({self.model})"

    def _get_headers(self) -> Dict[str, str]:
        """CLOVA Studio API 요청 헤더 생성"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "X-NCP-CLOVASTUDIO-REQUEST-ID": str(int(time.time() * 1000)),
            "Accept": "application/json",
        }

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 3000,
        temperature: float = 0.7,
        top_p: float = 0.8,
    ) -> Optional[HyperClovaXResponse]:
        """
        HyperCLOVA X 채팅 완성 API 호출
        순수 HyperCLOVA 응답 반환 (OpenAI 형식 변환 안 함)
        """
        if not self.api_key:
            print(">> HyperCLOVA X API 키가 설정되지 않음")
            return None

        request_data = {
            "messages": messages,
            "topP": top_p,
            "topK": 0,
            "maxTokens": min(max_tokens, 4096),
            "temperature": temperature,
            "repeatPenalty": 5.0,
            "stopBefore": [],
            "includeAiFilters": True,
            "seed": 0,
        }

        url = f"{self.base_url}/testapp/v1/chat-completions/{self.model}"
        headers = self._get_headers()

        try:
            print(f">> HyperCLOVA X API 호출 시작")
            print(f"   모델: {self.model}")
            print(f"   토큰: {max_tokens}, 온도: {temperature}")

            response = requests.post(
                url, headers=headers, json=request_data, timeout=60
            )

            print(f">> 응답 상태 코드: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print(f">> HyperCLOVA X API 응답 성공")

                # HyperCLOVA Response 객체로 래핑
                hyperclova_response = HyperClovaXResponse(result)

                print(f">> 생성된 텍스트 길이: {len(hyperclova_response.content)}자")
                print(
                    f">> 사용 토큰: 입력 {hyperclova_response.input_length} + 출력 {hyperclova_response.output_length} = {hyperclova_response.input_length + hyperclova_response.output_length}"
                )

                return hyperclova_response

            elif response.status_code == 401:
                print(f">> HyperCLOVA X API 인증 오류: {response.status_code}")
                print(f">> 오류 내용: {response.text}")
                print(">> API 키를 확인하세요")
                return None
            else:
                print(f">> HyperCLOVA X API 오류: {response.status_code}")
                print(f">> 오류 내용: {response.text}")
                return None

        except Exception as e:
            print(f">> HyperCLOVA X API 처리 중 오류: {e}")
            return None

    def is_available(self) -> bool:
        """API 키 설정 여부 확인"""
        return bool(self.api_key)

    def create_embedding(
        self, text: str, model: str = "clir-emb-dolphin"
    ) -> Optional[List[float]]:
        """
        HyperCLOVA X 임베딩 API 호출
        """
        if not self.api_key:
            print(">> HyperCLOVA X API 키가 설정되지 않음")
            return None

        request_data = {"text": text, "model": model}

        url = f"{self.base_url}/testapp/v1/api-tools/embedding/{model}"
        headers = self._get_headers()

        try:
            print(f">> HyperCLOVA X 임베딩 API 호출 시작")
            print(f"   모델: {model}")
            print(f"   텍스트 길이: {len(text)} 문자")

            response = requests.post(url, headers=headers, json=request_data)

            if response.status_code == 200:
                result = response.json()
                embedding = result.get("result", {}).get("embedding", [])
                print(f">> 임베딩 생성 성공 (차원: {len(embedding)})")
                return embedding
            else:
                print(f">> 임베딩 API 오류: {response.status_code}")
                print(f">> 응답: {response.text}")
                return None

        except Exception as e:
            print(f">> HyperCLOVA X 임베딩 API 호출 실패: {str(e)}")
            return None

    def _handle_request_error(self, e: Exception, operation: str) -> None:
        """요청 오류 처리"""
        error_msg = f">> HyperCLOVA X {operation} 실패: {str(e)}"
        print(error_msg)
        if hasattr(e, "response"):
            try:
                error_detail = e.response.json()
                print(f">> 오류 상세: {error_detail}")
            except:
                print(f">> 응답 상태 코드: {e.response.status_code}")


class MultiLLMClient:
    """여러 LLM 제공자를 지원하는 통합 클라이언트"""

    def __init__(self):
        self.hyperclova_client = None
        try:
            if settings.NAVER_CLOVA_API_KEY:
                self.hyperclova_client = HyperClovaXClient()
                print(">> MultiLLMClient: HyperCLOVA X 클라이언트 초기화 완료")
            else:
                print(">> MultiLLMClient: HyperCLOVA X API 키 없음")
        except Exception as e:
            print(f">> MultiLLMClient 초기화 실패: {e}")
            print(">> HyperCLOVA 사용이 비활성화되어 있습니다")

    def is_available(self) -> bool:
        """HyperCLOVA X API 사용 가능 여부 확인"""
        return self.hyperclova_client and self.hyperclova_client.is_available()

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 3000,
        temperature: float = 0.7,
        **kwargs,
    ) -> Optional[HyperClovaXResponse]:
        """HyperCLOVA X 채팅 완성 API"""
        if not self.hyperclova_client:
            print(">> HyperCLOVA X 클라이언트가 초기화되지 않았습니다")
            return None

        return self.hyperclova_client.chat_completion(
            messages=messages, max_tokens=max_tokens, temperature=temperature
        )

    def create_embedding(
        self, text: str, model: str = "clir-emb-dolphin"
    ) -> Optional[List[float]]:
        """HyperCLOVA X 임베딩 생성"""
        if not self.hyperclova_client:
            print(">> HyperCLOVA X 클라이언트가 초기화되지 않았습니다")
            return None

        return self.hyperclova_client.create_embedding(text=text, model=model)

    def test_connection(self) -> bool:
        """API 연결 테스트"""
        if not self.is_available():
            return False

        test_messages = [{"role": "user", "content": "안녕하세요. 연결 테스트입니다."}]

        result = self.chat_completion(
            messages=test_messages, max_tokens=50, temperature=0.5
        )

        return result is not None

    def _dummy_response(self, content: str) -> HyperClovaXResponse:
        """더미 응답 생성 (API 실패 시 사용)"""
        dummy_data = {
            "result": {
                "message": {"content": content},
                "inputLength": 0,
                "outputLength": len(content.split()),
                "stopReason": "stop",
            }
        }
        return HyperClovaXResponse(dummy_data)

        return result is not None
