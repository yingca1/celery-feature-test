```bash
cd t1

docker build . -t cft1

# start up local env stack
docker compose --env-file .env -f docker-compose.yml -p t1 up -d

# watch logging
docker compose --env-file .env -f docker-compose.yml -p t1 logs -f --tail 200

# shutdown local env stack
docker compose --env-file .env -f docker-compose.yml -p t1 down

# enter capture server container
docker compose --env-file .env -f docker-compose.yml -p t1 exec runtime bash

curl --location --request POST 'http://flower:5555/api/task/async-apply/blocking' \
--header 'Content-Type: application/json' \
--data-raw '{
    "args": [
        3
    ]
}'
```
