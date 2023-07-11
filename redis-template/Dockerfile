FROM redis:7.0.7-alpine3.17
COPY redis.conf /usr/local/etc/redis/redis.conf
RUN mkdir -p /var/lib/redis

EXPOSE 6379
CMD [ "redis-server", "/usr/local/etc/redis/redis.conf" ]
