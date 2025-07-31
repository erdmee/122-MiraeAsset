# 🚀 Railway 배포 가이드

## 사전 준비

1. **GitHub 저장소 준비**
   - 현재 프로젝트를 GitHub에 푸시
   - 모든 코드가 커밋되어 있는지 확인

2. **환경변수 준비**
   - HyperCLOVA X API 키
   - 기타 필요한 API 키들

## 배포 단계

### 1. Railway 계정 생성
1. [Railway.app](https://railway.app) 접속
2. "Start a New Project" 클릭
3. GitHub 계정으로 로그인

### 2. 백엔드 배포
1. "Deploy from GitHub repo" 선택
2. 저장소 선택
3. 배포 설정:
   ```
   Root Directory: backend
   Build Command: (자동)
   Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

### 3. 환경변수 설정
Railway 대시보드에서 다음 환경변수들을 설정:

```
HYPERCLOVA_API_KEY=실제_API_키
HYPERCLOVA_API_KEY_PRIMARY_VAL=실제_PRIMARY_키
HYPERCLOVA_REQUEST_ID=실제_REQUEST_ID
DB_PATH=/app/data/financial_data.db
ENVIRONMENT=production
DEBUG=false
```

### 4. 프론트엔드 배포
1. 새 서비스 추가
2. 같은 저장소 선택
3. 배포 설정:
   ```
   Root Directory: Frontend
   Build Command: npm run build
   Start Command: serve -s build -l $PORT
   ```

### 5. 환경변수 설정 (프론트엔드)
```
REACT_APP_API_URL=https://백엔드_도메인.railway.app
```

## 대안 배포 방법

### Vercel (프론트엔드만)
1. [Vercel.com](https://vercel.com) 가입
2. GitHub 저장소 연결
3. Frontend 폴더를 루트 디렉토리로 설정
4. 자동 배포

### Render
1. [Render.com](https://render.com) 가입
2. Web Service 생성
3. Docker 배포 선택

## 주의사항

1. **데이터베이스**: 현재 SQLite 사용 중 → 프로덕션에서는 PostgreSQL 권장
2. **파일 저장소**: 업로드된 파일들을 위한 외부 스토리지 필요할 수 있음
3. **메모리 제한**: 무료 티어에서는 메모리 제한이 있을 수 있음

## 비용

- **Railway**: 월 $5 무료 크레딧 (충분함)
- **Vercel**: 무료 (프론트엔드)
- **Render**: 무료 티어 제공

## 배포 후 확인사항

1. 모든 API 엔드포인트 작동 확인
2. 프론트엔드-백엔드 연결 확인
3. HyperCLOVA X API 연동 확인
4. 데이터베이스 연결 확인

## 트러블슈팅

### 일반적인 문제들
1. **CORS 오류**: 백엔드에서 프론트엔드 도메인 허용 설정
2. **환경변수 오류**: Railway 대시보드에서 확인
3. **빌드 실패**: 로그 확인 후 의존성 문제 해결

---

도움이 필요하면 언제든 문의하세요! 🎯
