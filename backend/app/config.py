# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
import os


class Settings(BaseSettings):
    # --- 기존에 정의하셨던 설정값들 ---
    OPENAI_API_KEY: Optional[str] = None
    DART_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    DB_PATH: str = "data/financial_data.db"
    CACHE_DIR: str = "data/cache"
    USER_AGENT: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    DEBUG: bool = True
    ALLOWED_ORIGINS: List[str] = ["*"]

    # --- 에러 로그에서 요구했던 누락된 필드들 추가 ---
    # .env 파일에 이 변수들이 정의되어 있어 에러가 발생했습니다.
    environment: str = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    max_news_count: int = 20
    max_disclosures_count: int = 10
    cache_duration_minutes: int = 30
    request_timeout: int = 10
    request_delay: float = 1.0

    # --- Pydantic v2 문법으로 설정 클래스 구성 ---
    # 기존의 class Config 대신 model_config 딕셔너리를 사용합니다.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # .env 파일에 정의되지 않은 추가 필드가 있어도 무시하고 에러를 내지 않음
    )


# 설정 인스턴스 생성
settings = Settings()

# 데이터 디렉토리 생성
# os.path.dirname()을 사용하여 파일이 아닌 디렉토리 경로를 확실히 합니다.
db_dir = os.path.dirname(settings.DB_PATH)
if db_dir:
    os.makedirs(db_dir, exist_ok=True)

os.makedirs(settings.CACHE_DIR, exist_ok=True)
