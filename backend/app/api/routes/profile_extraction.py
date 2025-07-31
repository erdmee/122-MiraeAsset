# app/api/routes/profile_extraction.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import json
import logging

from app.services.external.hyperclova_client import HyperClovaXClient

logger = logging.getLogger(__name__)
router = APIRouter()

class ProfileExtractionRequest(BaseModel):
    user_input: str
    previous_info: Dict[str, Any] = {}
    required_fields: List[str] = []

class ProfileExtractionResponse(BaseModel):
    extracted_info: Dict[str, Any]
    missing_fields: List[str]
    confidence_score: float
    follow_up_question: Optional[str] = None

@router.post("/profile-extraction", response_model=ProfileExtractionResponse)
async def extract_profile_info(request: ProfileExtractionRequest):
    """
    자연어 입력에서 사용자 프로필 정보를 추출하고 구조화된 JSON으로 변환
    """
    try:
        hyperclova_client = HyperClovaXClient()
        
        # 필수 필드 정의
        field_descriptions = {
            "name": "사용자의 이름 (한글 또는 영문)",
            "age": "사용자의 나이 (숫자)",
            "investment_experience": "투자 경험 수준 (초급, 중급, 고급 중 하나)",
            "risk_tolerance": "위험 허용도 (안전, 중위험, 고위험 중 하나)",
            "investment_goals": "투자 목표들의 배열 (예: ['장기성장', '안정적수익', '배당소득'])",
            "preferred_sectors": "관심 섹터들의 배열 (예: ['IT', '바이오', '금융'])",
            "investment_style": "투자 스타일 (가치투자, 성장투자, 배당투자, 기술주투자, 균형투자, 단타 중 하나)",
            "investment_amount_range": "투자 금액 범위 (1천만원 미만, 1천-5천만원, 5천만원-1억원, 1억원 이상 중 하나)"
        }
        
        # 이전 정보가 있다면 포함
        previous_info_text = ""
        if request.previous_info:
            previous_info_text = f"이전에 수집된 정보: {json.dumps(request.previous_info, ensure_ascii=False, indent=2)}"
        
        prompt = f"""당신은 투자 프로필 정보 추출 전문가입니다. 사용자의 자연어 입력에서 투자 관련 정보를 추출하여 JSON 형태로 구조화하세요.

{previous_info_text}

**추출해야 할 필드들:**
{json.dumps(field_descriptions, ensure_ascii=False, indent=2)}

**사용자 입력:**
"{request.user_input}"

**지침:**
1. 사용자 입력에서 명확히 언급된 정보만 추출하세요
2. 추측하지 말고, 확실한 정보만 포함하세요
3. 배열 필드의 경우 여러 값이 있으면 모두 포함하세요
4. 나이는 반드시 숫자로 변환하세요
5. investment_experience는 "초급", "중급", "고급" 중 하나로 정규화하세요
6. risk_tolerance는 "안전", "중위험", "고위험" 중 하나로 정규화하세요
7. investment_style는 "가치투자", "성장투자", "배당투자", "기술주투자", "균형투자", "단타" 중 하나로 정규화하세요
8. investment_amount_range는 "1천만원 미만", "1천-5천만원", "5천만원-1억원", "1억원 이상" 중 하나로 정규화하세요
9. '단타'는 investment_style로 분류하세요

**응답 형식 (JSON만 반환):**
{{
  "extracted_info": {{
    "field_name": "extracted_value"
  }},
  "confidence_score": 0.0-1.0,
  "missing_fields": ["field1", "field2"],
  "follow_up_question": "다음에 물어볼 질문 (선택사항)"
}}

응답:"""

        # HyperCLOVA X API 호출
        response = hyperclova_client.chat_completion([
            {"role": "user", "content": prompt}
        ], max_tokens=1000, temperature=0.3)
        
        if not response:
            raise HTTPException(status_code=500, detail="AI 응답을 받지 못했습니다.")
        
        # JSON 응답 파싱
        response_text = response.get_content().strip()
        
        # JSON 부분만 추출 (```json ... ``` 형태일 수 있음)
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        
        try:
            parsed_response = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 실패: {e}, 응답: {response_text}")
            # 기본 응답 반환
            parsed_response = {
                "extracted_info": {},
                "confidence_score": 0.0,
                "missing_fields": request.required_fields,
                "follow_up_question": "죄송합니다. 다시 한 번 말씀해 주시겠어요?"
            }
        
        # 이전 정보와 병합
        combined_info = {**request.previous_info, **parsed_response.get("extracted_info", {})}
        
        # 부족한 필드 계산
        missing_fields = []
        for field in request.required_fields:
            if field not in combined_info or not combined_info[field]:
                missing_fields.append(field)
            elif isinstance(combined_info[field], list) and len(combined_info[field]) == 0:
                missing_fields.append(field)
        
        return ProfileExtractionResponse(
            extracted_info=combined_info,
            missing_fields=missing_fields,
            confidence_score=parsed_response.get("confidence_score", 0.8),
            follow_up_question=parsed_response.get("follow_up_question")
        )
        
    except Exception as e:
        logger.error(f"프로필 추출 실패: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"프로필 정보 추출 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/profile-validation")
async def validate_profile_completeness(profile_data: Dict[str, Any]):
    """
    프로필 데이터의 완성도를 검증하고 부족한 정보 안내
    """
    try:
        required_fields = {
            "name": "이름",
            "age": "나이", 
            "investment_experience": "투자 경험",
            "risk_tolerance": "위험 허용도",
            "investment_goals": "투자 목표",
            "preferred_sectors": "관심 섹터",
            "investment_style": "투자 스타일",
            "investment_amount_range": "투자 금액 범위"
        }
        
        missing_fields = []
        validation_errors = []
        
        for field, description in required_fields.items():
            if field not in profile_data or not profile_data[field]:
                missing_fields.append(description)
            elif field == "age":
                try:
                    age = int(profile_data[field])
                    if age < 18 or age > 100:
                        validation_errors.append("나이는 18-100 사이여야 합니다.")
                except (ValueError, TypeError):
                    validation_errors.append("나이는 숫자여야 합니다.")
            elif field in ["investment_goals", "preferred_sectors"]:
                if not isinstance(profile_data[field], list) or len(profile_data[field]) == 0:
                    missing_fields.append(description)
        
        is_complete = len(missing_fields) == 0 and len(validation_errors) == 0
        
        return {
            "is_complete": is_complete,
            "missing_fields": missing_fields,
            "validation_errors": validation_errors,
            "completeness_score": (len(required_fields) - len(missing_fields)) / len(required_fields)
        }
        
    except Exception as e:
        logger.error(f"프로필 검증 실패: {e}")
        raise HTTPException(status_code=500, detail="프로필 검증 중 오류가 발생했습니다.")
