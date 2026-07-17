# Bare Redis on Railway's private network, mirroring the docker-compose setup:
# no password, reachable only via redis.railway.internal. protected-mode is
# disabled so other services on the private (IPv6) network can connect without auth.
FROM redis:7-alpine
EXPOSE 6379
CMD ["redis-server", "--protected-mode", "no", "--dir", "/data"]
