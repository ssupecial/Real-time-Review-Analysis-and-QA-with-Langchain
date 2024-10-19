FROM caddy:latest

# 환경 변수로 Caddyfile을 설정하는 스크립트 작성
COPY Caddyfile.template /etc/caddy/Caddyfile.template
COPY entrypoint.sh /usr/bin/entrypoint.sh
RUN chmod +x /usr/bin/entrypoint.sh

ENTRYPOINT ["/usr/bin/entrypoint.sh"]
