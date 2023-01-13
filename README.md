```bash
cd t1

# start up local env stack
docker compose --env-file .env -f docker-compose.yml -p t1 up -d

# watch logging
docker compose --env-file .env -f docker-compose.yml -p t1 logs -f --tail 200

# shutdown local env stack
docker compose --env-file .env -f docker-compose.yml -p t1 down

# enter capture server container
docker compose --env-file .env -f docker-compose.yml -p t1 exec runtime bash
```
