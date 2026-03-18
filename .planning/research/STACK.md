# Technology Stack — Docker Deployment

**Project:** Stecher Tennis (Docker Deployment)
**Domain:** Dockerizing a brownfield Flask+SocketIO+SQLite app with Caddy reverse proxy
**Researched:** 2026-03-18
**Overall confidence:** HIGH (core stack), MEDIUM (async worker recommendation)

---

## Recommended Stack

### Python Application Container

| Technology | Version/Tag | Purpose | Why |
|------------|-------------|---------|-----|
| `python:3.12-slim` | `python:3.12-slim` (rolling) | Base image for Flask app | Official multi-arch (amd64+arm64) image, Debian-based so prebuilt wheels work, 41MB compressed vs 17MB Alpine but Alpine breaks bcrypt/cryptography/greenlet wheels during arm64 builds |
| gunicorn | `23.x` (from prod-requirements.txt) | WSGI server | Production-grade, already in prod-requirements.txt |
| eventlet | `>=0.35` | Async worker class for Flask-SocketIO | App already uses it; **do not migrate during this Docker milestone** |

**Why not Alpine?** Alpine uses musl libc instead of glibc. `bcrypt`, `cryptography`, and `greenlet` all ship prebuilt wheels for glibc targets. Alpine forces recompilation from source, which (a) adds 10+ minutes to ARM64 cross-compilation via QEMU emulation and (b) occasionally produces silent runtime bugs. The 24MB size saving is not worth the risk on a brownfield project.

**Why not `python:3.12` (full image)?** Full image is 350MB+ compressed. Slim cuts that to ~41MB with no meaningful functionality loss for a Flask app.

**Why not uv-managed Python?** uv's managed Python (recommended by pythonspeed.com Feb 2026) is the optimal long-term choice, but adds complexity that is out of scope for this Docker milestone. Stick with the official image.

### Gunicorn Command (Critical — Single Worker)

```
gunicorn --worker-class eventlet --workers 1 --bind 0.0.0.0:5000 \
         --timeout 120 --access-logfile - --error-logfile - \
         app:app
```

**Why exactly 1 worker?** Flask-SocketIO's load balancer does not support sticky sessions across processes. Multiple workers break WebSocket connections. This is not negotiable with eventlet or gevent — it is a hard constraint of the Socket.IO protocol when no message queue (Redis/RabbitMQ) is present.

**Why `--timeout 120`?** Default gunicorn timeout is 30s. WebSocket long-poll fallback connections can hold open longer; 120s prevents premature worker kills.

**Why `--access-logfile -`?** Docker log collection reads stdout/stderr. Logging to files inside a container means the logs are invisible to `docker compose logs`.

### Async Worker: Eventlet vs Gevent (Decision Point)

The Flask-SocketIO maintainer (Miguel Grinberg) stated in 2025 that eventlet "is winding down and will eventually be closed" and recommends threading mode for low-traffic apps or gevent for high-traffic. However:

**For this milestone, keep eventlet.** Rationale:
- The app already works with eventlet in production on the RPi
- Gunicorn will not remove eventlet until version 26.0 (no release date set as of March 2026)
- Migrating async mode is an application code change, not a Docker infrastructure change
- The tennis club app is low-traffic — eventlet's limitations are irrelevant at this scale

**Future consideration (out of scope now):** If the app ever needs migration, the path is: eventlet → `simple-websocket` + `--worker-class gthread --threads 100` (maintainer's recommendation for low-traffic apps like this one). This avoids the gevent-websocket dependency (which has not been updated in 5+ years).

### Caddy Reverse Proxy Container

| Technology | Version/Tag | Purpose | Why |
|------------|-------------|---------|-----|
| `caddy:2-builder` | `caddy:2-builder` | Multi-stage build stage only | xcaddy tool for compiling custom modules |
| `caddy:2` | `caddy:2` | Runtime reverse proxy | Official image, auto-updates to latest 2.x (2.11.x as of Mar 2026), native multi-arch |

**Why a custom Caddy build?** The standard `caddy:2` image does not include the DuckDNS DNS challenge provider. DuckDNS requires DNS-01 ACME challenge (not HTTP-01) because DuckDNS subdomains route to private IPs and Let's Encrypt cannot reach port 80 for HTTP challenge validation. The `caddy-dns/duckdns` module must be compiled in via xcaddy.

**Custom Caddy Dockerfile pattern (multi-stage):**
```dockerfile
FROM caddy:2-builder AS builder
RUN xcaddy build \
    --with github.com/caddy-dns/duckdns

FROM caddy:2
COPY --from=builder /usr/bin/caddy /usr/bin/caddy
```

This produces a final image of normal Caddy size (~45MB) with only the DuckDNS module added.

**Why not `serfriz/caddy-duckdns` (pre-built community image)?** The serfriz image is auto-updated on Caddy releases and is a reasonable option. However, building from source via xcaddy gives full control of module versions and avoids trusting a third-party image for a security-critical component (TLS termination). The official two-stage build pattern is equally simple.

**Why `caddy:2` (not `caddy:2.11.1`)?** The `caddy:2` floating tag always pulls the latest stable 2.x. For a home/club deployment, getting security patches automatically is desirable. For a locked-version production system, pin to `caddy:2.11.1` (current as of Mar 2026).

**Existing Caddyfile pattern (from `documentation/99_rpi.txt`) — works as-is in Docker:**
```
tc-breakpoint-forderung.duckdns.org {
    tls {
        dns duckdns {env.DUCKDNS_TOKEN}
    }

    reverse_proxy app:5000 {
        header_up Host {http.request.host}
        header_up X-Real-IP {http.request.remote}
        header_up X-Forwarded-For {http.request.remote}
        header_up X-Forwarded-Proto {http.request.scheme}
    }
}
```

The only change from the manual setup: `localhost:8000` becomes `app:5000` (Docker service name resolution), and `tls email` becomes `tls { dns duckdns ... }` for DNS-01 challenge.

### Docker Compose

| Feature | Decision | Why |
|---------|----------|-----|
| File format | Compose v2 (no `version:` key) | `version:` field is obsolete since Docker Compose v2.0; Docker Desktop and modern CLI ignore it, but its presence generates deprecation warnings |
| Healthcheck | Yes, on `app` service | Caddy `depends_on` with `condition: service_healthy` prevents Caddy from starting before Flask is ready |
| Named volume for SQLite | Yes | Named Docker volumes avoid host UID/GID permission mismatches that bind mounts cause. Bind mounts work but require `chown` matching the container user |
| Named volume for Caddy data | Yes | TLS certificates must survive container restarts and rebuilds |
| `.env` file | Yes | `docker compose` automatically loads `.env` from the same directory; secrets (SECRET_KEY, DUCKDNS_TOKEN) never appear in compose YAML |
| `restart: unless-stopped` | Yes on both services | Survives RPi reboots without systemd |

**Compose service structure:**
```yaml
services:
  app:
    build: .
    restart: unless-stopped
    volumes:
      - tennis_data:/app/data
    environment:
      - SECRET_KEY
      - FLASK_DEBUG=false
      - CORS_ALLOWED_ORIGINS=https://tc-breakpoint-forderung.duckdns.org
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s

  caddy:
    build:
      context: ./caddy
      dockerfile: Dockerfile
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"
    volumes:
      - ./caddy/Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    environment:
      - DUCKDNS_TOKEN
    depends_on:
      app:
        condition: service_healthy

volumes:
  tennis_data:
  caddy_data:
  caddy_config:
```

### Multi-Architecture Build

| Approach | Decision | Why |
|----------|----------|-----|
| Build tool | `docker buildx` with QEMU emulation | Standard approach for single-machine cross-builds; arm64 is slow under QEMU on x86 but acceptable for infrequent builds |
| Base image support | `python:3.12-slim` and `caddy:2` both support amd64+arm64 natively | No custom cross-compilation logic needed in Dockerfile |
| Build target | `linux/amd64,linux/arm64` | Covers x86 server and Raspberry Pi 4/5 (arm64) |
| Push requirement | Must `--push` to registry for multi-arch | Docker cannot load multi-arch manifests locally; must push to registry (e.g., Docker Hub or GHCR) |
| Local workflow | Build for native arch only during development | `docker compose build` without `--platform` builds for host arch, which is faster |

**Build command for multi-arch release:**
```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --push \
  -t yourrepo/stecher-tennis:latest \
  .
```

**Deploy command on RPi (pull pre-built image):**
```bash
docker compose pull && docker compose up -d
```

### Dockerfile — Multi-Stage Python App

**Stage 1 (builder):** Install all Python dependencies into a virtualenv. This stage can use build tools.
**Stage 2 (runtime):** Copy only the virtualenv and application code. No pip, no build tools.

```dockerfile
FROM python:3.12-slim AS builder
WORKDIR /build
COPY prod-requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r prod-requirements.txt

FROM python:3.12-slim
# Non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser
WORKDIR /app
# Copy installed packages from builder
COPY --from=builder /install /usr/local
# Copy application
COPY --chown=appuser:appuser . .
# Create data directory for SQLite volume mount
RUN mkdir -p /app/data && chown appuser:appuser /app/data
USER appuser
EXPOSE 5000
CMD ["gunicorn", "--worker-class", "eventlet", "--workers", "1", \
     "--bind", "0.0.0.0:5000", "--timeout", "120", \
     "--access-logfile", "-", "--error-logfile", "-", "app:app"]
```

**Why multi-stage?** The builder stage installs pip, wheel, and compilation headers. These are not needed at runtime. Multi-stage removes them from the final image, reducing attack surface and image size by ~30-50MB.

**Why `/app/data` subdirectory for SQLite?** Mounting a Docker volume at `/app` would hide all application files copied during build. Mounting at `/app/data` only exposes that subdirectory to the volume while keeping application code intact. The app startup path for the database file must be changed from `tennis.db` to `data/tennis.db`.

### SQLite Volume and WAL Mode

| Concern | Decision | Rationale |
|---------|----------|-----------|
| Volume type | Named Docker volume | Avoids host UID/GID mismatch; Docker manages ownership |
| WAL mode | Keep enabled | WAL mode works fine on local Docker volumes (ext4/overlay2); it only fails on NFS/SMB network mounts |
| File permissions | Non-root user owns `/app/data` | Set via `chown appuser:appuser /app/data` in Dockerfile RUN before switching to USER |
| Backup | Out of scope for Docker milestone | Existing cron backup pattern (`backup_tennis_db.sh`) can be adapted to use `docker exec` later |

**Warning:** If a bind mount is used instead of a named volume (e.g., `./data:/app/data`), the host directory must be `chown`-ed to match the UID of `appuser` inside the container, or SQLite will fail to open the file for writing.

### Supporting Tools

| Tool | Use | Notes |
|------|-----|-------|
| `.dockerignore` | Exclude `.git`, `__pycache__`, `*.pyc`, `documentation/`, `*.db`, `.env`, `conda-*` from build context | Reduces build context size from ~500MB to <10MB; `.db` excluded so the Docker image never contains user data |
| `curl` | Healthcheck probe inside app container | Must be installed in the slim image (`RUN apt-get install -y --no-install-recommends curl`) |
| `docker buildx` | Multi-arch builds | Comes with Docker Desktop and Docker Engine 23+; verify with `docker buildx version` |

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Base image | `python:3.12-slim` | `python:3.12-alpine` | Alpine breaks prebuilt wheels for bcrypt, cryptography, greenlet; forces source compilation; arm64 builds are much slower |
| Base image | `python:3.12-slim` | `python:3.12` (full) | Full image is ~350MB vs ~41MB; no extra functionality needed for Flask app |
| Async worker | eventlet (keep existing) | gevent | Migration requires app code changes; out of scope for Docker milestone; app is low-traffic |
| Async worker | eventlet (keep existing) | simple-websocket + gthread | Same as above — future path when eventlet is removed from gunicorn |
| Caddy DNS module | Build via xcaddy (official pattern) | `serfriz/caddy-duckdns` | Third-party image for TLS termination; xcaddy build is equally simple and stays under project control |
| Caddy DNS challenge | DNS-01 (DuckDNS) | HTTP-01 (standard) | HTTP-01 requires Let's Encrypt to reach port 80 from the internet; DuckDNS subdomains may resolve to private IPs which blocks HTTP challenge |
| Volume for SQLite | Named Docker volume | Bind mount | Bind mounts require matching UIDs on host; named volumes avoid this |
| Compose format | No `version:` key | `version: "3.8"` | `version:` is deprecated in Docker Compose v2 and generates warnings |

---

## Installation

```bash
# On build machine (verify buildx is available)
docker buildx version

# Create a multi-arch builder if not already configured
docker buildx create --use --name multiarch-builder

# Build and push multi-arch image
docker buildx build --platform linux/amd64,linux/arm64 --push \
  -t yourrepo/stecher-tennis:latest .

# On target server (RPi or x86)
docker compose pull
docker compose up -d

# Verify health
docker compose ps
docker compose logs -f
```

---

## Confidence Assessment

| Area | Confidence | Source | Notes |
|------|------------|--------|-------|
| `python:3.12-slim` base image | HIGH | [pythonspeed.com Feb 2026](https://pythonspeed.com/articles/base-image-python-docker-images/), [Docker Hub official](https://hub.docker.com/_/python/) | Verified multi-arch support, confirmed slim>alpine for this stack |
| Multi-stage Dockerfile pattern | HIGH | Docker official docs, widely used pattern | Standard best practice |
| Gunicorn `--workers 1` with eventlet | HIGH | [Flask-SocketIO docs](https://flask-socketio.readthedocs.io/en/latest/deployment.html) | Hard constraint, documented explicitly |
| Eventlet status (keep for now) | MEDIUM | [GitHub discussion #2068](https://github.com/miguelgrinberg/Flask-SocketIO/discussions/2068) | Maintainer recommends against new use, but removal timeline unclear; existing code works |
| Caddy xcaddy DuckDNS build | HIGH | [Caddy official docs](https://caddyserver.com/docs/running#docker-compose), [caddy-dns/duckdns repo](https://github.com/caddy-dns/duckdns) | Well-documented, official pattern |
| Caddy version (2.11.x) | MEDIUM | [Tux Machines Apr 2025](https://news.tuxmachines.org/n/2025/04/20/Caddy_2_10_Web_Server_Debuts_Enhanced_TLS_Privacy.shtml), WebSearch | 2.11.x confirmed; exact patch version not independently verified in official release page |
| Named volume for SQLite | HIGH | SQLite official forum + Docker docs | WAL on local Docker volumes confirmed safe; NFS warning documented |
| Multi-arch buildx approach | HIGH | [Docker official multi-platform docs](https://docs.docker.com/build/building/multi-platform/) | Standard tooling, well-documented |
| `.env` file auto-loading in Compose | HIGH | Docker Compose v2 official behavior | Default behavior, widely confirmed |

---

## Sources

- [Best Docker base image for Python (Feb 2026)](https://pythonspeed.com/articles/base-image-python-docker-images/)
- [Official Python Docker Hub image](https://hub.docker.com/_/python/)
- [Flask-SocketIO Deployment Docs](https://flask-socketio.readthedocs.io/en/latest/deployment.html)
- [Flask-SocketIO Discussion: Is Eventlet Still The Best Option?](https://github.com/miguelgrinberg/Flask-SocketIO/discussions/2068)
- [Flask-SocketIO Discussion: eventlet, gevent or simple-websocket?](https://github.com/miguelgrinberg/Flask-SocketIO/discussions/1915)
- [Caddy Docker Compose Guide (official)](https://caddyserver.com/docs/running#docker-compose)
- [caddy-dns/duckdns module](https://github.com/caddy-dns/duckdns)
- [Caddy 2.10 release notes](https://news.tuxmachines.org/n/2025/04/20/Caddy_2_10_Web_Server_Debuts_Enhanced_TLS_Privacy.shtml)
- [Docker Multi-Platform Build Docs](https://docs.docker.com/build/building/multi-platform/)
- [How to Build Multi-Architecture Docker Images (Jan 2026)](https://oneuptime.com/blog/post/2026-01-06-docker-multi-architecture-images/view)
- [SQLite in Docker — permissions and WAL (Feb 2026)](https://oneuptime.com/blog/post/2026-02-08-how-to-run-sqlite-in-docker-when-and-how/view)
- [Gunicorn Docker Guide](https://gunicorn.org/guides/docker/)

---

*Researched: 2026-03-18*
