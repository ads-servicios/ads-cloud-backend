# ADS Cloud Backend

FastAPI API for the ADS platform. Own git repo — deploy independently from frontend.

## Stack

- Python 3.12, FastAPI, SQLAlchemy (async), Alembic, PostgreSQL

## Layout

- `app/` — API (routes, controllers, models, schemas)
- `alembic/` — database migrations

## Local run (without Docker)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

## Docker (standalone)

Same layout as `frontend/` — each microservice owns its Docker files:

| File | Purpose |
|------|---------|
| `Dockerfile` | API image |
| `docker-compose.yml` | API + Postgres |
| `.dockerignore` | Build context exclusions |
| `.env.example` | Env template |

```bash
cp .env.example .env
docker compose up --build
```

API: http://localhost:8000 — Swagger: http://localhost:8000/docs

## Full stack (with frontend)

```bash
cd ../docker
docker compose up --build
```

## Migrations

```bash
cd ../docker
docker compose run --rm api alembic revision --autogenerate -m "description"
docker compose run --rm api alembic upgrade head
```

## Tests

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest -q
```

## Auth (AS-52 / AS-53)

JWT Bearer authentication. Public routes: `GET /health`, `POST /contact`.  
Protected: `GET /auth/me`, `/users` CRUD, `/roles` CRUD. Login: `POST /auth/login`.

Authorization is **role → scope → action** (DB). Seeded matrix:

| role | scope | actions |
|------|-------|---------|
| administrator | users | read, list, create, edit, delete |
| common | users | read |
| administrator | roles | read, list, create, edit, delete |

### First admin (migration seed)

Alembic `0003` creates (idempotent) administrator:

- email: `ads.serviciosintegrales@gmail.com`
- password: `admin123456`
- `must_change_password=true`

After first login, call `POST /auth/force-change-password` with `{ "new_password": "..." }` (Bearer). New users created via API also start with `must_change_password=true`.

| Variable | Purpose |
|----------|---------|
| `JWT_SECRET` | HMAC secret (required outside development) |
| `JWT_ALGORITHM` | Default `HS256` |
| `JWT_EXPIRE_MINUTES` | Access token TTL (default 60) |
| `BOOTSTRAP_ADMIN_EMAIL` / `BOOTSTRAP_ADMIN_PASSWORD` | Optional fallback if DB has no users |

```bash
# Login
curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"ads.serviciosintegrales@gmail.com","password":"admin123456"}'

# Forced password change (when must_change_password is true)
curl -s -X POST http://localhost:8000/auth/force-change-password \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"new_password":"your-strong-password"}'

# List users (needs users:list)
curl -s http://localhost:8000/users \
  -H "Authorization: Bearer <access_token>"

# Manage roles (needs roles:* — administrator)
curl -s http://localhost:8000/roles \
  -H "Authorization: Bearer <access_token>"
```

In Swagger (`/docs`), use **Authorize** with the Bearer token from login.

## SMTP (contact form)

Secrets are **never committed**. SES SMTP from `contacto@ads-inversiones.es`.

```bash
cp .env.development.example .env   # then set SMTP_USER + SMTP_PASSWORD from SSM
```

| Variable | Value |
|----------|-------|
| `EMAIL_PROVIDER` | `smtp` |
| `SMTP_HOST` | `email-smtp.eu-north-1.amazonaws.com` |
| `CONTACT_EMAIL_FROM` | `contacto@ads-inversiones.es` |
| `CONTACT_EMAIL_TO` | `ads.serviciosintegrales@gmail.com` |
| `SMTP_USER` / `SMTP_PASSWORD` | SSM `/ads/shared/contact/*` after Terraform apply |

Confirmation email (AS-50): HTML template with logo CID; dual send (internal + visitor).

| Variable | Purpose |
|----------|---------|
| `CONTACT_PUBLIC_WEBSITE_URL` | CTA button URL per environment |
| `CONTACT_FOOTER_EMAIL` / `CONTACT_FOOTER_WEBSITE` | Footer in confirmation email |
| `CONTACT_CONFIRMATION_SUBJECT` | `RE: confirmacion de solicitud` |

Setup: `ads-devops/docs/SES-SETUP.md`

On AWS: `./scripts/entrypoint-aws.sh uvicorn app.main:app --host 0.0.0.0 --port 8000`

Deploy scripts and CI live at the umbrella root: `../` (`ads-cloud-system/`).
