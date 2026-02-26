# 1. 빌드 스테이지 (Node.js 환경)
FROM node:20-alpine AS builder

WORKDIR /app

# 패키지 매니저 파일들 복사
COPY package.json package-lock.json ./
RUN npm ci

# 소스코드 복사 및 빌드 실행 (`dist` 디렉토리 생성)
COPY . .
RUN npm run build

# 2. 런타임 프로덕션 스테이지 (Nginx 기반 가벼운 웹서버)
FROM nginx:alpine

# 앞서 작성해둔 Nginx 커스텀 라우팅 설정 파일 복사
COPY nginx.conf /etc/nginx/conf.d/default.conf

# builder 스테이지에서 만들어진 결과물 복사
COPY --from=builder /app/dist /usr/share/nginx/html

# 기본 HTTP 포트
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
