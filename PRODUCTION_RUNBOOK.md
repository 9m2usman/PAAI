# PAAI Production Runbook

## 1. Configuration

Copy `.env.example` to `.env` and configure:
- `GROQ_API_KEY`
- `PAAI_AUTH_SECRET`: random secret of at least 32 characters.
- Explicit `PAAI_CORS_ORIGINS` for trusted browser origins.
- Google OAuth values only when Google integrations are enabled.

Never commit `.env`. Store production secrets in a managed secret store, not in the container image.

Generate an encryption key for future encrypted credential storage:

```powershell
.\\venv\\Scripts\\python.exe -c "from app.production.crypto import CredentialCipher; print(CredentialCipher.generate_key())"
```

The current Fernet helper is not yet integrated into the in-memory Phase 5 CredentialManager. Do not assume existing OAuth credentials are encrypted at rest.

## 2. Run locally

```powershell
.\\venv\\Scripts\\python.exe -m pip install -r requirements.txt
.\\venv\\Scripts\\python.exe -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000
```

Check `http://127.0.0.1:8000/health/live` and `/health/ready`.

Run the background worker in another terminal:

```powershell
.\\venv\\Scripts\\python.exe -m app.production.worker_main
```

## 3. Docker Compose

```powershell
docker compose build
docker compose up -d
docker compose ps
docker compose logs -f api
```

The Compose file persists the data directory in a named volume. Place the API behind a TLS-terminating reverse proxy before exposing it publicly.

## 4. Backups and recovery

Back up authentication, memory, and autonomy databases together using a consistent SQLite backup process. Protect backups as sensitive data. Periodically test restoration into an isolated environment.

## 5. Operations

- Verify health endpoints after deployment.
- Monitor logs and request IDs.
- Alert on repeated worker failures, authentication failures, due-goal backlog, and database disk exhaustion.
- Rotate authentication/encryption keys only with a planned migration.
- Keep TLS, firewall, OS patching, secret storage, and database backups configured at the hosting layer.

## 6. Deployment boundary

The included deployment is a single-host SQLite setup. It is not a multi-region or horizontally scaled service. Do not run multiple API/worker replicas against the same SQLite files without a shared locking and storage design. A multi-instance deployment should move to PostgreSQL and a shared queue/lease backend.

A repository with Docker files is not evidence of a secure production deployment. Perform load/security tests, backups/restore drills, monitoring setup, and live deployment verification before handling real user data.
