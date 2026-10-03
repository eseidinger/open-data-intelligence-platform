# Local data services

Start the local PostgreSQL and MinIO services from the repository root:

```bash
docker compose --file infrastructure/compose/docker-compose.yml up --detach
docker compose --file infrastructure/compose/docker-compose.yml ps
```

PostgreSQL is available at `localhost:5432` with database, username, and password `odip`. MinIO AIStor serves its S3-compatible API at `http://localhost:9000` and its development console at `http://localhost:9001` with username `odip` and password `odip-local-development`.

These credentials are for local development only. Stop the services with `docker compose --file infrastructure/compose/docker-compose.yml down`. Add `--volumes` only when intentionally deleting all local data.
