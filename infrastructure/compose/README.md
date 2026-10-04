# Local data services

Start the local PostgreSQL service from the repository root:

```bash
docker compose --file infrastructure/compose/docker-compose.yml up --detach
docker compose --file infrastructure/compose/docker-compose.yml ps
```

PostgreSQL is available at `localhost:5432` with database, username, and password `odip`.

These credentials are for local development only. Stop the services with `docker compose --file infrastructure/compose/docker-compose.yml down`. Add `--volumes` only when intentionally deleting all local data.
