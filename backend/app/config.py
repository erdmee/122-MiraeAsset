from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
import os


class Settings(BaseSettings):
    # --- 기존에 정의하셨던 설정값들 ---
    OPENAI_API_KEY: Optional[str] = None
    DART_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    # --- HyperCLOVA X API 설정 ---
    NAVER_CLOVA_API_KEY: Optional[str] = None
    NAVER_CLOVA_API_HOST: str = "clovastudio.stream.ntruss.com"
    NAVER_CLOVA_MODEL: str = "HCX-003"  # 실제 모델명 사용
    USE_HYPERCLOVA: bool = True

    # --- HeyGen API 설정 ---
    HEYGEN_API_KEY: Optional[str] = None

    # --- 데이터베이스 및 캐시 설정 ---
    DB_PATH: str = "data/financial_data.db"
    CACHE_DIR: str = "data/cache"
    USER_AGENT: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    DEBUG: bool = True
    ALLOWED_ORIGINS: List[str] = ["*"]

    # --- 서버 설정 ---
    environment: str = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # --- 데이터 수집 설정 ---
    max_news_count: int = 20
    max_disclosures_count: int = 10
    cache_duration_minutes: int = 30
    request_timeout: int = 10
    request_delay: float = 1.0

    # --- Pydantic v2 문법으로 설정 클래스 구성 ---
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# 설정 인스턴스 생성
settings = Settings()

# 데이터 디렉토리 생성
db_dir = os.path.dirname(settings.DB_PATH)
if db_dir:
    os.makedirs(db_dir, exist_ok=True)

os.makedirs(settings.CACHE_DIR, exist_ok=True)


# 설정 확인 함수
def check_api_settings():
    """API 설정 상태 확인"""
    print("=== API 설정 상태 ===")
    print(f"OpenAI API Key: {'설정됨' if settings.OPENAI_API_KEY else '미설정'}")
    print(f"DART API Key: {'설정됨' if settings.DART_API_KEY else '미설정'}")
    print(f"HyperCLOVA API Key: {'설정됨' if settings.NAVER_CLOVA_API_KEY else '미설정'}")
    print(f"HeyGen API Key: {'설정됨' if settings.HEYGEN_API_KEY else '미설정'}")
    print(f"HyperCLOVA 사용: {settings.USE_HYPERCLOVA}")
    print(f"새로운 CLOVA API 사용: {settings.USE_NEW_CLOVA_API}")
    print(f"CLOVA API 호스트: {settings.NAVER_CLOVA_API_HOST}")
    print("==================")


if __name__ == "__main__":
    check_api_settings()
