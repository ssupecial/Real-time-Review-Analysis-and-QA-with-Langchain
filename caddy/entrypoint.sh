#!/bin/sh

# .env 파일에서 받은 환경 변수를 Caddyfile.template에 적용
envsubst < /etc/caddy/Caddyfile.template > /etc/caddy/Caddyfile

# Caddy 실행
caddy run --config /etc/caddy/Caddyfile --adapter caddyfile
