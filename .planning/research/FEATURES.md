# Feature Landscape

**Domain:** Docker deployment of Flask+SocketIO+SQLite+Caddy app (Raspberry Pi + x86)
**Researched:** 2026-03-18
**Confidence:** MEDIUM-HIGH (official docs verified for most claims)

---

## Table Stakes

Features that must exist for this to be a real production Docker deployment. Missing any of these makes the system broken or insecure.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Multi-stage Dockerfile (build vs runtime) | Keeps final image small; separates pip install from app execution | Low | Use `python:3.12-slim` as runtime base — Alpine breaks scipy/numpy C extensions on ARM |
| `.dockerignore` file | Prevents secrets (.env, tennis.db), virtualenvs, and .git from entering the image | Low | Must exclude: `.env`, `tennis.db`, `__pycache__`, `venv`, `.git` |
| Named Docker volume for SQLite database | Data must survive `docker compose down` and image rebuilds | Low | Mount the volume to the exact path the app uses; bind mount is also acceptable for direct host access to the file |
| Non-root container user | Security baseline; prevents privilege escalation if container is compromised | Low | Create a dedicated user (e.g. `appuser`) in Dockerfile; use `COPY --chown` |
| Gunicorn with `--workers 1 --worker-class eventlet` | Flask-SocketIO with eventlet requires exactly one worker — multiple workers cause "invalid session" errors | Low | This is a hard constraint, not a preference. Already validated in production |
| Environment configuration via `.env` file | `SECRET_KEY`, `CORS_ALLOWED_ORIGINS`, `FLASK_DEBUG`, `DUCKDNS_TOKEN` must not be hardcoded | Low | `.env` passed via `env_file:` in compose; never copied INTO the image |
| Caddy reverse proxy service in Compose | Handles TLS termination, HTTP→HTTPS redirect, WebSocket proxy headers | Low | Caddy official image; requires `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto` headers for Flask's ProxyFix |
| Caddy data + config named volumes | TLS certificates must survive container restarts | Low | Two volumes: `/data` (certs) and `/config` (runtime config). Without these, Caddy re-requests certs on every restart — risks Let's Encrypt rate limits |
| `restart: unless-stopped` policy | Both services must auto-start after system reboot | Low | `unless-stopped` is preferred over `always` (respects intentional `docker compose stop`) |
| `app_net` internal Docker network | App and Caddy communicate on internal network; app never exposes port 5000 to host | Low | Caddy proxies to `app:5000` (container name), not `localhost:5000` |
| HTTP/3 + HTTPS port exposure | Caddy needs `80:80` (HTTP-01 challenge + redirect) and `443:443` (HTTPS) and `443:443/udp` (HTTP/3) | Low | Only Caddy exposes ports; Flask container has no `ports:` section |
| Multi-architecture image (linux/amd64 + linux/arm64) | Same image must run on both development x86 machine and production Raspberry Pi 4 (ARM64) | Medium | Use `docker buildx build --platform linux/amd64,linux/arm64`; requires QEMU on build machine |
| SQLite file ownership and permissions | Non-root user inside container must have write access to the volume-mounted SQLite file | Low | Set correct `uid:gid` on `chown` in Dockerfile or use `user:` in compose; WAL mode needs write permission on both `tennis.db` and `tennis.db-wal` |

---

## Differentiators

Features that raise reliability and operability above baseline but are not strictly required for the app to function.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| `/health` endpoint in Flask | Enables Docker `HEALTHCHECK`, lets Caddy `depends_on: condition: service_healthy` | Low | Single route returning `{"status": "ok"}` and HTTP 200; does not touch DB |
| Docker `HEALTHCHECK` instruction in Dockerfile | Docker marks container unhealthy before Caddy starts routing to it; prevents routing to a broken app on startup | Low | `CMD curl -f http://localhost:5000/health \|\| exit 1`; needs `curl` in runtime image |
| `depends_on: condition: service_healthy` in Compose | Caddy does not start until Flask is confirmed healthy; eliminates 502 errors during initial startup | Low | Requires the HEALTHCHECK above |
| DuckDNS DNS-01 challenge via custom Caddy build | Allows automatic wildcard / DNS certificates without opening port 80 inbound — cleaner for home routers | Medium | Requires building custom Caddy image with `caddy-dns/duckdns` module; env var `DUCKDNS_API_TOKEN`. The official `caddy` Docker image does NOT include DNS provider modules. |
| Gunicorn `--timeout` and `--keep-alive` tuning | Prevents worker timeouts during slow WebSocket upgrades; avoids dropped connections | Low | `--timeout 120 --keep-alive 5` matches existing systemd config |
| Gunicorn access log to stdout | Structured logs visible via `docker compose logs`; no log file management needed | Low | `--access-logfile -` sends to stdout; Docker captures it |
| Caddyfile log level ERROR only | Reduces log noise in production; only actionable events appear in `docker compose logs caddy` | Low | Already validated in existing Caddyfile |
| SQLite WAL mode set in app init | Improves concurrent read performance; reduces lock contention under SocketIO events | Low | Already in use — confirm it fires on container start, not just on fresh DB creation |

---

## Anti-Features

Things to deliberately NOT build. These would add complexity without value for a single-host club app with ~50 users.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Multiple Gunicorn workers | Flask-SocketIO sessions are per-process; multiple workers cause "invalid session" errors unless a message queue (Redis) is added | Hard constraint: always use `--workers 1` |
| Redis/message queue for SocketIO | Only needed for multi-worker or multi-host scaling; massive complexity increase | Single eventlet worker handles all WebSocket sessions |
| PostgreSQL migration | SQLite + WAL mode is fine for a club app with dozens of users; migration adds setup complexity | Keep SQLite, persist via volume |
| Docker Secrets (Swarm mode) | Secrets are for Docker Swarm/Kubernetes; Docker Compose on a single host has no secrets management — `.env` is sufficient and conventional | Use `.env` file, add it to `.gitignore` |
| Kubernetes / Docker Swarm | Over-engineered for single-host deployment on a Raspberry Pi | `docker compose up -d` is the entire orchestration layer needed |
| Monitoring stack (Prometheus + Grafana) | Not justified for a tennis club ranking app; adds ~500MB to the deployment | `docker compose logs` is sufficient |
| CI/CD pipeline | Manual `docker compose pull && docker compose up -d` is fine for infrequent updates to a club app | Document the update procedure instead |
| Separate static file server (Nginx for statics) | Flask + Caddy serves statics adequately at this scale; Nginx adds another container and config surface | Caddy reverse proxy handles everything |
| Alpine as base image | Alpine uses musl libc which breaks binary wheels for scipy, numpy, pydantic (C extensions). ARM + Alpine = painful cross-compile | Use `python:3.12-slim` (Debian-based) |
| Pinning ALL transitive dependencies | `requirements.txt` with pinned versions is enough; pip-compile for every transitive dep is overkill here | Pin direct deps in `prod-requirements.txt`; let pip resolve transitive |
| Build-time secrets in Docker ARG | ARG values appear in image history — never use for SECRET_KEY or API tokens | Inject at runtime via `.env` / `env_file:` |

---

## Feature Dependencies

```
/health endpoint
  → Docker HEALTHCHECK in Dockerfile
      → depends_on: condition: service_healthy (in Compose)

Custom Caddy image (DuckDNS module)
  → DUCKDNS_API_TOKEN in .env
  → Caddyfile acme_dns directive

Non-root user in Dockerfile
  → Volume file ownership must match that user's UID/GID
      → SQLite WAL files (tennis.db-wal, tennis.db-shm) must be writable

Multi-arch build (buildx)
  → python:3.12-slim base (not Alpine — musl breaks scipy on ARM)
  → QEMU installed on build machine OR native ARM builder

Named volume for SQLite
  → App writes DB to a known path (e.g. /app/tennis.db)
  → Dockerfile sets that path as the volume mount point
```

---

## MVP Recommendation

For the Dockerization milestone, implement these in order:

1. **Dockerfile** — multi-stage, `python:3.12-slim`, non-root user, single-worker gunicorn entrypoint
2. **`.dockerignore`** — exclude `.env`, `tennis.db`, `__pycache__`, `.git`, `venv`
3. **`docker-compose.yml`** — app service + caddy service, internal network, named volumes, `restart: unless-stopped`, env_file
4. **Caddyfile** — reverse proxy to `app:5000` (not localhost), WebSocket headers, `unless-stopped`
5. **`/health` endpoint + HEALTHCHECK** — simple, no DB check needed
6. **Multi-arch build** — `docker buildx build --platform linux/amd64,linux/arm64`

Defer unless specifically requested:
- DuckDNS custom Caddy build (HTTP-01 challenge via port 80 works fine if the existing setup continues working; only needed if port 80 is blocked at the router)
- Gunicorn log tuning (functionally optional)

---

## Sources

- Flask-SocketIO deployment docs (official): https://flask-socketio.readthedocs.io/en/latest/deployment.html — MEDIUM confidence (single worker constraint confirmed authoritatively)
- Docker Flask+Gunicorn guide: https://testdriven.io/blog/dockerizing-flask-with-postgres-gunicorn-and-nginx/ — MEDIUM confidence
- Caddy Docker Compose official docs: https://caddyserver.com/docs/running#docker-compose — HIGH confidence (official)
- Docker Python best practices: https://testdriven.io/blog/docker-best-practices/ — MEDIUM confidence
- Caddy DuckDNS community thread: https://caddy.community/t/caddy-docker-with-duckdns/18682 — MEDIUM confidence (community verified)
- Multi-arch buildx: https://docs.docker.com/build/building/multi-platform/ — HIGH confidence (official Docker docs)
- Docker security best practices 2025: https://nerdleveltech.com/mastering-docker-best-practices-for-2025 — LOW confidence (third-party, consistent with official guidance)
- Existing production setup (`documentation/99_rpi.txt`) — HIGH confidence (validated in actual deployment)
