# MedStock Rural API: Milestone A1 (Foundation)

Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic. SQLite for development, PostgreSQL for staging and production.

## First-time setup (from `apps/api`)

```bash
python3.12 -m venv .venv
source .venv/bin/activate            # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install pip-tools
pip-compile requirements.in -o requirements.txt
pip-compile requirements-dev.in -o requirements-dev.txt
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env                 # Windows: copy .env.example .env
ruff format . && ruff check --fix .  # one-off tidy so CI's format check starts green
```

Commit `requirements.txt` and `requirements-dev.txt` (CI installs from them).

## Run

```bash
alembic upgrade head
uvicorn app.main:create_app --factory --reload
curl -i http://localhost:8000/api/v1/health
```

Interactive docs: http://localhost:8000/api/v1/docs

## Test

```bash
pytest -q                                   # SQLite (default)

# PostgreSQL (from the repo root: docker compose up -d db)
TEST_DATABASE_URL=postgresql+psycopg://medstock:medstock@localhost:5432/medstock_test pytest -q
# Windows PowerShell:
#   $env:TEST_DATABASE_URL="postgresql+psycopg://medstock:medstock@localhost:5432/medstock_test"; pytest -q

ruff check . && ruff format --check . && mypy
```

WARNING: the PostgreSQL run wipes the `public` schema of the database named in
`TEST_DATABASE_URL`. The harness refuses to run unless the database name contains "test".

## Contract (docs/contract)

```bash
python -m app.contract export   # regenerate openapi.json, enums.json, errors.json
python -m app.contract check    # fail if the committed files are out of date (CI runs this)
```

After changing any schema, route, enum or error code, run `export` and commit the result.
See `docs/contract/README.md` for the change procedure (additive vs breaking).

## Layout

```
app/core      config, db (engine + unit of work), types, errors, schemas, request-id middleware
app/models    the 17 tables (columns and constraints only), Base, UUID mixin
app/api       health, plus v1/ with one router per area; security, idempotency, support helpers
app/schemas   request and response schemas per area (separate from database models)
app/services  business logic (empty until A6)
migrations    Alembic env, baseline, and revisions 0002 to 0006 (the schema)
tests         harness, probe tables, tests for every A1 rule
```

## Conventions later milestones must follow

- Services open transactions: `with db.unit_of_work(write=True) as session:`. Routers never commit.
- `Mapped[datetime]` is always timezone-aware UTC; naive datetimes are rejected.
- Enums use `string_enum(MyEnum, "name")` (VARCHAR + named CHECK), never native enums.
- CHECK constraints, multi-column unique constraints and indexes need explicit names.
- Request and response schemas inherit `ApiModel` (unknown fields rejected).
- Raise `AppError(code, message, status_code=...)` for expected failures.

## Stub endpoints

Endpoints that are in the contract but not built return `501 NOT_IMPLEMENTED`. When a milestone
implements one, replace the `not_implemented()` call in its route (keep the signature), and add
its operationId to `IMPLEMENTED` in `tests/test_contract.py`.

## Database

The schema is described in `docs/database.md`. Apply it with `alembic upgrade head`.
`tests/factories.py` builds valid rows for tests; `tests/test_constraints.py` shows every rule
the database enforces by breaking it on purpose.
