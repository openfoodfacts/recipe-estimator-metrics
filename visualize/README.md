# visualization

A tentative to visualize the data using SQL and having dashboards and so on.

## Creating the database

```bash
python3 -m venv venv
. venv/bin/activate
python create_db.py --force  superset/local_db/tests.duckdb ../test-sets/results/
```

If file extension is sqlite, a sqlite database is created (for redash)
otherwise it's a duckdb database.

## Superset

Note: not yet meant for public exposition (only on localhost)

Edit your docker/.env-local file to add a secret and admin passwords etc !
```
SUPERSET_LOAD_EXAMPLES=no
SUPERSET_SECRET_KEY=super-secret
DATABASE_PASSWORD=super-pass
POSTGRES_PASSWORD=another-pass
```

and go to 8088 by default.

It works with duckdb

## Redash docker

Note: not yet mean for public exposition (only on localhost)

Before starting:
```bash
docker compose run --rm server ./manage.py database create_tables
```

Then:
```bash
docker compose up
```

And go to http://localhost:5000
