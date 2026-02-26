#!/bin/bash

echo "================================================"
echo "🚀 Starting Billing AI Assistant (Local Dev) "
echo "================================================"

# 도커 실행시에는 포트 충돌로 인해 사용 안될 수 있음
# npx concurrently를 사용하여 로그를 접두어(SERVER/CLIENT)와 색상별로 분리하여 깔끔하게 보여줍니다.
# --kill-others 옵션으로 하나가 종료(Ctrl+C)되면 나머지도 함께 종료되도록 합니다.

npx concurrently \
  --names "SERVER,CLIENT" \
  --prefix-colors "blue.bold,green.bold" \
  --kill-others \
  "uv run python backend/main.py" \
  "npm run dev --prefix frontend"
