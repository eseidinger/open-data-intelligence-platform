# Local data services

Start the local PostgreSQL and S3-compatible object-store services from the repository root:

```bash
docker compose --file infrastructure/compose/docker-compose.yml up --detach
docker compose --file infrastructure/compose/docker-compose.yml ps
```

PostgreSQL is available at `localhost:5432` with database, username, and password `odip`. SeaweedFS serves an S3-compatible API at `http://localhost:9000`, with access key `odip`, secret key `odip-local-development`, and the local `odip-raw` bucket.

These credentials are for local development only. Stop the services with `docker compose --file infrastructure/compose/docker-compose.yml down`. Add `--volumes` only when intentionally deleting all local data.
