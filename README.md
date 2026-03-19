# API Gateway — Distributed Rate Limiting with FastAPI

A production-grade API Gateway built with **FastAPI**, **PostgreSQL**, **Redis**, and **JWT authentication**. Implements a sliding-window rate limiter using atomic Lua scripts in Redis, with per-user and per-endpoint enforcement.

> **Verified working** on Windows (PowerShell + Docker Desktop), macOS, and Linux.

---

## Architecture

```
Client
  │
  ▼
┌─────────────────────────────────────────────────────┐
│                  FastAPI Application                 │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │           GatewayMiddleware                  │  │
│  │  1. Check route — exempt or protected?       │  │
│  │  2. Extract & validate X-API-Key header      │  │
│  │  3. Run sliding-window rate limiter (Redis)  │  │
│  │  4. Inject X-RateLimit-* response headers    │  │
│  │  5. Log request to PostgreSQL                │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  Routes:                                            │
│    /api/v1/auth/*       ← Public (no auth)         │
│    /api/v1/users/*      ← JWT bearer token         │
│    /api/v1/api-keys/*   ← JWT bearer token         │
│    /api/v1/logs/*       ← JWT bearer token         │
│    /api/v1/gateway/*    ← X-API-Key + rate limit   │
│    /health              ← Public                   │
└─────────────────────────────────────────────────────┘
         │                          │
         ▼                          ▼
   PostgreSQL 16               Redis 7
  (users, api_keys,         (sliding window
   request_logs)             sorted sets)
```

### Auth model — two separate schemes

| Route group | Auth header | Issued by |
|---|---|---|
| `/api/v1/auth/*` | none | — |
| `/api/v1/users/*`, `/api/v1/api-keys/*`, `/api/v1/logs/*` | `Authorization: Bearer <jwt>` | `/auth/login` |
| `/api/v1/gateway/*` | `X-API-Key: gw_...` | `/api-keys` endpoint |

> Do **not** mix them — sending a JWT to a gateway route or an API key to a user route will return 401.

### Rate limiting — sliding window via Redis Lua

Each request against a gateway route is checked with an atomic Lua script operating on a Redis sorted set keyed `rl:{user_id}:{endpoint}`:

1. **Prune** — remove entries older than the window
2. **Count** — get current usage
3. **Gate** — if count ≥ limit → 429
4. **Record** — add entry with `score = now_ms`, set TTL

Single `EVALSHA` call — race-condition-free at any concurrency. Fails open if Redis is unreachable.

---

## Quick Start

### Option A — Docker (recommended)

No local Python, PostgreSQL, or Redis installation required.

```powershell
# 1. Unzip and enter the project
cd C:\path\to\api_gateway

# 2. Copy environment config
copy .env.example .env
# Open .env and set SECRET_KEY and JWT_SECRET_KEY to random 32+ char strings
# Generate one with: python -c "import secrets; print(secrets.token_hex(32))"

# 3. Build and start all services
docker compose up --build

# 4. In a second terminal — seed dev users and API keys
docker compose exec app python scripts/seed.py

# 5. Open Swagger UI in browser
Start-Process "http://localhost:8000/docs"
```

> **Note:** If you see `the attribute version is obsolete` — this is a harmless Docker Compose v2 warning. Remove the `version:` line from `docker-compose.yml` to silence it.

### Option B — Local Python

Prerequisites: Python 3.12+, PostgreSQL 14+, Redis 6+

```powershell
# 1. Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows PowerShell
# source .venv/bin/activate     # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env
# Edit .env — set DATABASE_URL, REDIS_URL, SECRET_KEY, JWT_SECRET_KEY

# 4. Create the PostgreSQL database
psql -U postgres -c "CREATE DATABASE api_gateway;"

# 5. Run migrations
alembic upgrade head

# 6. Seed dev data (optional but recommended)
python scripts/seed.py

# 7. Start the server
uvicorn app.main:app --reload --port 8000
```

---

## Usage — Windows PowerShell

> PowerShell's built-in `curl` is an alias for `Invoke-WebRequest` and **does not accept** `-X`, `-H`, or `-d` flags.
> Always use `Invoke-RestMethod` as shown below, or install real curl: `winget install curl.curl` and use `curl.exe`.

### 1. Health check

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health"
```

### 2. Register a new user

```powershell
Invoke-RestMethod -Method POST `
  -Uri "http://localhost:8000/api/v1/auth/register" `
  -ContentType "application/json" `
  -Body '{"email":"you@example.com","password":"Secret123"}'
```

> Password must be 8+ characters with at least one uppercase letter and one digit.

### 3. Login and save the JWT token

```powershell
$response = Invoke-RestMethod -Method POST `
  -Uri "http://localhost:8000/api/v1/auth/login" `
  -ContentType "application/json" `
  -Body '{"email":"you@example.com","password":"Secret123"}'

$TOKEN = $response.access_token
Write-Host "Token: $($TOKEN.Substring(0,20))..."
```

### 4. Create an API key

```powershell
$key = Invoke-RestMethod -Method POST `
  -Uri "http://localhost:8000/api/v1/api-keys" `
  -Headers @{ Authorization = "Bearer $TOKEN" } `
  -ContentType "application/json" `
  -Body '{"name":"My Key","rate_limit":50,"rate_limit_window":60}'

$API_KEY = $key.key
Write-Host "API Key: $API_KEY"
```

> The full key (starting with `gw_`) is shown once — save it. Subsequent `GET /api-keys` responses redact the key.

### 5. Call a rate-limited gateway endpoint

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/gateway/ping" `
  -Headers @{ "X-API-Key" = $API_KEY }
```

Expected response:
```
pong  user_id                               rate_limit_remaining
----  -------                               --------------------
True  78f3abfd-af79-42c4-92d8-7497204d9391  49
```

### 6. Test the echo endpoint

```powershell
Invoke-RestMethod -Method POST `
  -Uri "http://localhost:8000/api/v1/gateway/echo" `
  -Headers @{ "X-API-Key" = $API_KEY } `
  -ContentType "application/json" `
  -Body '{"message":"Hello from API Gateway!"}'
```

### 7. Test rate limiting — watch the 429s kick in

```powershell
1..55 | ForEach-Object {
  try {
    $r = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/gateway/ping" `
      -Headers @{ "X-API-Key" = $API_KEY }
    Write-Host "[$_] 200 OK — remaining: $($r.rate_limit_remaining)"
  } catch {
    Write-Host "[$_] 429 RATE LIMITED"
  }
}
```

Expected output — requests 1–50 succeed, 51–55 are rejected:
```
[1]  200 OK — remaining: 49
[2]  200 OK — remaining: 48
...
[50] 200 OK — remaining: 0
[51] 429 RATE LIMITED
[52] 429 RATE LIMITED
[53] 429 RATE LIMITED
[54] 429 RATE LIMITED
[55] 429 RATE LIMITED
```

### 8. View request logs

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:8000/api/v1/logs?page=1&page_size=10" `
  -Headers @{ Authorization = "Bearer $TOKEN" }
```

### 9. List your API keys

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:8000/api/v1/api-keys" `
  -Headers @{ Authorization = "Bearer $TOKEN" }
```

### 10. Refresh a JWT token

```powershell
$refresh = Invoke-RestMethod -Method POST `
  -Uri "http://localhost:8000/api/v1/auth/refresh" `
  -ContentType "application/json" `
  -Body "{`"refresh_token`":`"$($response.refresh_token)`"}"

$TOKEN = $refresh.access_token
```

---

## Usage — macOS / Linux

```bash
# Health check
curl http://localhost:8000/health

# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"Secret123"}'

# Login — save the token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"Secret123"}' \
  | jq -r .access_token)

# Create an API key
API_KEY=$(curl -s -X POST http://localhost:8000/api/v1/api-keys \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"My Key","rate_limit":50,"rate_limit_window":60}' \
  | jq -r .key)

# Call the gateway
curl -v http://localhost:8000/api/v1/gateway/ping \
  -H "X-API-Key: $API_KEY"

# Test rate limiting
for i in $(seq 1 55); do
  curl -s -o /dev/null -w "[$i] %{http_code}\n" \
    http://localhost:8000/api/v1/gateway/ping \
    -H "X-API-Key: $API_KEY"
done
```

---

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/auth/register` | — | Register a new user |
| POST | `/api/v1/auth/login` | — | Login → JWT access + refresh tokens |
| POST | `/api/v1/auth/refresh` | — | Rotate token pair |
| GET | `/api/v1/users/me` | JWT | Get own profile and API keys |
| PATCH | `/api/v1/users/me` | JWT | Update email or password |
| DELETE | `/api/v1/users/me` | JWT | Deactivate account |
| POST | `/api/v1/api-keys` | JWT | Create a new API key |
| GET | `/api/v1/api-keys` | JWT | List all keys (key value redacted) |
| PATCH | `/api/v1/api-keys/{id}` | JWT | Update name or rate limit |
| DELETE | `/api/v1/api-keys/{id}` | JWT | Revoke a key |
| GET | `/api/v1/logs` | JWT | Paginated request log |
| GET | `/api/v1/gateway/ping` | API Key | Rate-limited ping |
| POST | `/api/v1/gateway/echo` | API Key | Rate-limited echo |
| GET | `/api/v1/gateway/data` | API Key | Simulated data fetch |
| GET | `/api/v1/gateway/data/{id}` | API Key | Fetch single item |
| GET | `/health` | — | Health check |

### Rate limit exceeded — 429 response

```json
{
  "detail": "Rate limit exceeded. Try again later.",
  "limit": 50,
  "window_seconds": 60
}
```

Response headers on every gateway request:
```
X-RateLimit-Limit: 50
X-RateLimit-Remaining: 49
X-RateLimit-Used: 1
X-Response-Time-Ms: 3
Retry-After: 60        ← only present on 429 responses
```

---

## Configuration

All settings are loaded from environment variables. Copy `.env.example` to `.env` and edit:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | — | PostgreSQL async URL (`postgresql+asyncpg://user:pass@host:5432/db`) |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `SECRET_KEY` | — | App secret — min 32 chars, change in production |
| `JWT_SECRET_KEY` | — | JWT signing secret — min 32 chars, change in production |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token TTL in minutes |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token TTL in days |
| `DEFAULT_RATE_LIMIT` | `100` | Default requests per window |
| `DEFAULT_RATE_LIMIT_WINDOW` | `60` | Window size in seconds |
| `LOG_LEVEL` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`) |
| `APP_ENV` | `development` | Environment name |
| `DEBUG` | `false` | Enables SQL query logging when `true` |

Generate a secure key:
```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Running Tests

Tests use an in-memory SQLite database — no PostgreSQL or Redis required to run them.

**Docker:**
```powershell
docker compose exec app pip install aiosqlite --quiet
docker compose exec app pytest -v
```

**Local:**
```powershell
pip install aiosqlite
pytest -v

# With coverage report
pip install pytest-cov
pytest --cov=app --cov-report=term-missing
```

Expected output:
```
tests/test_auth.py          6 passed
tests/test_api_keys.py      5 passed
tests/test_users.py         5 passed
tests/test_security.py      6 passed
tests/test_rate_limiter.py  5 passed

25 passed in ~4s
```

---

## Project Structure

```
api_gateway/
├── app/
│   ├── api/v1/
│   │   ├── endpoints/
│   │   │   ├── auth.py          # Register, login, token refresh
│   │   │   ├── users.py         # Profile CRUD
│   │   │   ├── api_keys.py      # API key CRUD
│   │   │   ├── logs.py          # Paginated request logs
│   │   │   └── gateway.py       # Rate-limited demo endpoints
│   │   └── router.py            # Aggregates all routers under /api/v1
│   ├── core/
│   │   ├── config.py            # Pydantic-settings (reads .env)
│   │   ├── logging.py           # Loguru — rotating file + console
│   │   └── security.py          # JWT sign / verify / refresh
│   ├── db/
│   │   ├── session.py           # Async SQLAlchemy engine + session factory
│   │   └── redis.py             # Async Redis connection pool
│   ├── middleware/
│   │   └── gateway.py           # API key auth + rate limiting + request logging
│   ├── models/
│   │   ├── user.py              # User ORM model
│   │   ├── api_key.py           # APIKey ORM model (auto-generates gw_ prefixed keys)
│   │   └── request_log.py       # RequestLog ORM model
│   ├── schemas/
│   │   ├── user.py              # UserCreate / UserResponse (password strength validation)
│   │   ├── api_key.py           # APIKeyCreate / APIKeyResponse / APIKeyPublic (redacted)
│   │   └── auth.py              # LoginRequest / TokenResponse / RequestLogPage
│   ├── services/
│   │   ├── rate_limiter.py      # Sliding-window via atomic Lua script in Redis
│   │   ├── user_service.py      # User CRUD — uses bcrypt directly (no passlib)
│   │   ├── api_key_service.py   # API key CRUD + usage tracking
│   │   └── log_service.py       # Paginated log queries
│   └── main.py                  # App factory, lifespan, CORS, exception handlers
├── alembic/
│   ├── env.py                   # Async migration runner
│   └── versions/001_initial.py  # Creates users, api_keys, request_logs tables
├── tests/
│   ├── conftest.py              # Async fixtures, SQLite test DB, HTTP client
│   ├── test_auth.py             # Register, login, refresh, password validation
│   ├── test_api_keys.py         # Create, list, update, revoke keys
│   ├── test_users.py            # Profile, update, deactivate
│   ├── test_security.py         # JWT sign/verify/tamper
│   └── test_rate_limiter.py     # Sliding window, fail-open, per-endpoint isolation
├── scripts/
│   └── seed.py                  # Creates admin + regular user with API keys
├── Dockerfile                   # Multi-stage build (builder + runtime, non-root user)
├── docker-compose.yml           # app + PostgreSQL 16 + Redis 7 + one-shot migrator
├── requirements.txt             # bcrypt 4.0.1 (passlib removed — compatibility fix)
├── alembic.ini
├── pytest.ini
└── .env.example
```

---

## Bugs Fixed During Setup

### 1. bcrypt / passlib incompatibility

`passlib 1.7.4` is incompatible with `bcrypt 4.x` — it tries to read `bcrypt.__about__.__version__` which no longer exists in bcrypt 4, then crashes during an internal wrap-bug detection check.

**Symptom:**
```
AttributeError: module 'bcrypt' has no attribute '__about__'
ValueError: password cannot be longer than 72 bytes
```

**Fix:** `passlib` removed entirely. `bcrypt` called directly in `app/services/user_service.py`:

```python
# requirements.txt — passlib[bcrypt]==1.7.4 replaced with:
bcrypt==4.0.1

# app/services/user_service.py
import bcrypt

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
```

---

### 2. Middleware blocking JWT-protected routes

The original `GatewayMiddleware` exempt list only included `/api/v1/auth`. All other routes — including `/api/v1/api-keys`, `/api/v1/users`, and `/api/v1/logs` — were incorrectly demanding an `X-API-Key` header, making it impossible to create API keys via JWT auth.

**Symptom:**
```json
{"detail": "X-API-Key header is required"}
```
...when calling `POST /api/v1/api-keys` with a valid JWT bearer token.

**Fix:** Exempt list expanded in `app/middleware/gateway.py`:

```python
_EXEMPT_PREFIXES = (
    "/api/v1/auth",
    "/api/v1/users",      # added
    "/api/v1/api-keys",   # added
    "/api/v1/logs",       # added
    "/docs",
    "/redoc",
    "/openapi.json",
    "/health",
)
```

---

### 3. PowerShell curl alias (Windows)

PowerShell's `curl` is a built-in alias for `Invoke-WebRequest`, which does not accept Unix-style flags (`-X`, `-H`, `-d`).

**Symptom:**
```
Invoke-WebRequest : A parameter cannot be found that matches parameter name 'X'.
```

**Fix options:**
- Use `Invoke-RestMethod` with PowerShell syntax (shown throughout this README)
- Install real curl permanently: `winget install curl.curl`, then use `curl.exe` to bypass the alias

---

## Design Decisions

- **Fail-open rate limiter** — if Redis is temporarily unavailable, requests pass through rather than taking the service down
- **Atomic Lua script** — the entire check-and-increment is a single Redis `EVALSHA` call, preventing race conditions under high concurrency
- **Per-endpoint isolation** — Redis keys are `rl:{user_id}:{endpoint}`, so `/ping` and `/data` have independent windows per user
- **Middleware logging** — request logs and usage counts are written in the same DB session as the rate limit check, saving a roundtrip
- **Direct bcrypt** — no passlib wrapper, eliminating a class of version-compatibility failures
- **Multi-stage Docker build** — builder stage installs gcc and compiles packages; runtime stage copies only the venv, keeping the final image ~120 MB
- **Non-root container user** — the app runs as `appuser`, not root, reducing attack surface
