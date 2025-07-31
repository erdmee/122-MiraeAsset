FROM node:18

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

# 프로덕션 빌드 생성
RUN npm run build

# 정적 파일 서빙을 위한 serve 설치
RUN npm install -g serve

ENV PORT=3000

# 빌드된 파일을 서빙
CMD ["serve", "-s", "build", "-l", "3000"]
