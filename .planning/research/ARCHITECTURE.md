# Architecture Patterns: Docker Deployment

**Domain:** Flask + SQLite + Caddy containerized deployment
**Researched:** 2026-03-18
**Overall Confidence:** HIGH (verified against Flask-SocketIO docs, Caddy official docs, Docker buildx docs)

---

## Recommended Architecture

Two-container Docker Compose stack connected via a shared internal bridge network. The app container runs gunicorn with a single eventlet worker. The Caddy container is a custom build that includes the DuckDNS DNS module. SQLite data persists via a named Docker volume mounted into the app container only.

```
Internet
    |
  :443 (HTTPS)
  :80  (HTTP → redirect to HTTPS)
    |
[ caddy container ]   <--- custom build: caddy:2-builder + xcaddy + caddy-dns/duckdns
    |                       ports: 80:80, 443:443, 443:443/udp
    |  internal bridge network (tennis_net)
    |  upstream: http://app:5000
    |
[ app container ]     <--- python:3.12-slim, multi-stage build
    |                       internal port 5000 only (NOT exposed to host)
    |                       gunicorn --workers 1 --worker-class eventlet
    |
[ named volume: tennis_data ]
    |
  /app/data/tennis.db   (inside container)
```

---

## Container Boundaries

### app container

| Attribute | Value |
|-----------|-------|
| Base image | `python:3.12-slim` (multi-stage) |
| Process | `gunicorn --workers 1 --worker-class eventlet --bind 0.0.0.0:5000 --timeout 120 app:app` |
| Internal port | 5000 (not mapped to host) |
| Volumes | `tennis_data:/app/data` |
| User | non-root (e.g., UID 1000, created in Dockerfile) |
| Env vars | SECRET_KEY, CORS_ALLOWED_ORIGINS, FLASK_DEBUG, DB_PATH |
| Networks | tennis_net |
| Health check | `GET /health` or `GET /login` → HTTP 200 |

**Single worker is non-negotiable.** Flask-SocketIO with eventlet cannot run with multiple gunicorn workers because gunicorn's load balancer has no sticky session support. Using more than one worker causes "Invalid session" errors. This is documented in the Flask-SocketIO deployment guide and confirmed by the existing systemd configuration.

### caddy container

| Attribute | Value |
|-----------|-------|
| Base image | Custom build from `caddy:2-builder` via xcaddy |
| DNS module | `github.com/caddy-dns/duckdns` |
| Host ports | `80:80`, `443:443`, `443:443/udp` |
| Volumes | `./Caddyfile:/etc/caddy/Caddyfile`, `caddy_data:/data`, `caddy_config:/config` |
| Env vars | `DUCKDNS_TOKEN`, `DOMAIN` |
| Networks | tennis_net |
| Communicates with | app container via service name `app:5000` |

**Why a custom Caddy build:** The official `caddy:2` Docker image does not include DNS provider modules. To use the DuckDNS DNS-01 ACME challenge (which the existing deployment uses via Caddy's `tls email@domain.com` directive), the image must be built with `xcaddy` including `caddy-dns/duckdns`. This is a two-stage Dockerfile pattern.

**Why DuckDNS DNS-01 challenge:** The existing deployment uses Caddy's ACME integration with a DuckDNS domain. The DNS-01 challenge does not require port 80 to be available during certificate issuance — a useful property for home/RPi setups where ISPs may block port 80. Caddy handles certificate renewal automatically; certificates persist in the `caddy_data` named volume.

---

## Network Architecture

### Internal Bridge Network (tennis_net)

Docker Compose creates a named bridge network. Both containers join it. The Caddy container refers to the Flask app using the Docker Compose service name as the hostname: `http://app:5000`.

The app container does NOT expose port 5000 to the host. Only Caddy exposes ports 80 and 443 to the host. This is correct isolation: the Flask app is unreachable except through Caddy.

```yaml
networks:
  tennis_net:
    driver: bridge
```

### WebSocket Proxying through Caddy

Caddy v2 handles WebSocket upgrades automatically — no special `upgrade` directives are needed for basic WebSocket proxying. The `reverse_proxy` directive passes through the `Upgrade` and `Connection` headers. The existing deployment's nginx-style headers (`header_up Host`, `header_up X-Forwarded-For`, etc.) are still recommended for Flask-Login session integrity and CORS origin matching.

Minimum working Caddyfile for this stack:

```
{$DOMAIN} {
    tls {
        dns duckdns {$DUCKDNS_TOKEN}
    }

    reverse_proxy app:5000 {
        header_up Host {http.request.host}
        header_up X-Real-IP {http.request.remote}
        header_up X-Forwarded-For {http.request.remote}
        header_up X-Forwarded-Proto {http.request.scheme}
    }
}
```

This matches the existing working Caddyfile from `documentation/99_rpi.txt`, just replacing `localhost:8000` with `app:5000` and adding the DNS challenge block.

---

## Volume Architecture

### Named Volume: tennis_data

```
Host (Docker volume driver)  →  /app/data/  (inside app container)
                                        ↓
                                 tennis.db  (SQLite WAL mode)
                                 tennis.db-wal
                                 tennis.db-shm
```

**Why named volume over bind mount:** Named volumes give Docker full ownership control, making non-root user permissions straightforward. Bind mounts require the host UID to match the container UID, which is error-prone across machines and architectures.

**SQLite + WAL mode + non-root user:** SQLite's WAL mode creates `.db-wal` and `.db-shm` sidecar files with the same permissions as the main `.db` file. All three files must be owned by the container user. Using a named volume and setting ownership in the Dockerfile entrypoint (or via a `chown` in the Dockerfile) ensures the non-root container user can write to these files. The app code already enables WAL mode — this does not need to change.

**DB path in app:** The app currently hardcodes the path to `tennis.db`. It must be made configurable via an environment variable (e.g., `DB_PATH=/app/data/tennis.db`) so the volume mount location can be specified without changing application code per environment.

### Named Volumes: caddy_data, caddy_config

```
caddy_data:/data     — ACME certificates (persists across container restarts)
caddy_config:/config — Caddy runtime config state
```

These must be named volumes (not bind mounts) to ensure certificate state survives container rebuilds without triggering ACME re-issuance. Let's Encrypt rate-limits issuance; losing the `caddy_data` volume means re-requesting certificates, which can hit rate limits quickly during development.

---

## Multi-Architecture Build Pipeline

### Strategy: Build and Push to Registry

Docker buildx cannot load multi-arch images to the local Docker daemon directly — `--push` is required, which pushes to a container registry. This means a registry must exist before multi-arch builds can work in a single command.

**Options:**
1. **Docker Hub** (public or private): simplest, free for public images
2. **GitHub Container Registry (ghcr.io)**: free, integrates with GitHub
3. **Local registry container**: run a `registry:2` container on the build machine, use `--push` to it

For a private club app, option 3 (local registry) or option 1 (private Docker Hub repo) are appropriate.

### Build Commands

```bash
# One-time setup: create buildx builder with multi-arch support
docker buildx create --name multiarch --driver docker-container --use
docker buildx inspect --bootstrap

# Build and push app image
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag registry/tennis-app:latest \
  --push \
  ./

# Build and push caddy image
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag registry/tennis-caddy:latest \
  --push \
  ./caddy/
```

### Base Image Compatibility

`python:3.12-slim` supports both `linux/amd64` and `linux/arm64` (HIGH confidence — Python official images ship multi-arch manifests for these platforms). `caddy:2-builder` also supports both platforms. No cross-compilation complications expected for pure Python code.

### Alternative: Single-Arch Build on Target

If a registry is not available, build the image directly on the target machine (RPi or x86 server):

```bash
# On the target machine
docker build -t tennis-app:local .
```

This is simpler for a single-host deployment and avoids registry setup. The tradeoff is that the image is not portable across architectures without rebuilding.

---

## Multi-Stage Dockerfile Pattern (app container)

```
Stage 1: builder
  FROM python:3.12-slim AS builder
  - install build tools (gcc, etc.)
  - pip install --no-cache-dir -r requirements.txt into /install

Stage 2: runtime
  FROM python:3.12-slim
  - copy /install from builder
  - create non-root user (appuser, UID 1000)
  - COPY app source
  - set DB_PATH env var default
  - HEALTHCHECK
  - CMD gunicorn --workers 1 --worker-class eventlet ...
```

The multi-stage build ensures build tools (gcc, headers) are absent from the final image. The runtime stage is minimal: python:3.12-slim + installed packages + app source only.

---

## Data Flow

### HTTP/HTTPS Request Flow

```
Browser → :443 → Caddy (TLS termination)
       → header_up headers added
       → http://app:5000 (internal network)
       → gunicorn (eventlet worker)
       → Flask route handler
       → SQLite (via /app/data/tennis.db)
       → JSON/HTML response
       → Caddy → Browser
```

### WebSocket (Socket.IO) Flow

```
Browser → :443/socket.io → Caddy (WebSocket upgrade, automatic)
       → http://app:5000/socket.io (upgrade header passed through)
       → gunicorn eventlet worker (persistent connection)
       → Flask-SocketIO event handlers
       → emit_data_update() broadcasts to connected clients
```

**Critical:** The single eventlet worker handles all WebSocket connections. Caddy must not buffer WebSocket connections — buffering must be disabled for the Socket.IO path. Caddy's default configuration does not buffer streaming connections.

### Database Access Flow

```
Flask route handler
  → get_db() (thread-local SQLite connection)
  → /app/data/tennis.db (named volume)
  → WAL mode: concurrent reads OK, serialized writes
  → close_db() on request teardown
```

---

## Build Order (Dependencies)

Components must be built and started in this order:

1. **Create volumes first** (Docker Compose handles this automatically on `up`)
   - `tennis_data` — must exist before app starts
   - `caddy_data`, `caddy_config` — must exist before Caddy starts

2. **Build caddy image** (no dependency on app)
   - xcaddy build takes longer than app build
   - Build in parallel with app image if using separate build stages

3. **Build app image** (no dependency on Caddy)
   - Multi-stage Python build

4. **Start app container first** (Caddy depends on app being reachable)
   - Use `depends_on` in Docker Compose with health check condition
   - Caddy will retry upstream connections, so a short startup delay is tolerable

5. **Start Caddy container** (after app is healthy)
   - Caddy performs ACME certificate provisioning on first start
   - Certificate is cached in `caddy_data` volume for subsequent starts

**Docker Compose `depends_on` pattern:**

```yaml
services:
  caddy:
    depends_on:
      app:
        condition: service_healthy
```

This requires a `HEALTHCHECK` in the app Dockerfile or `healthcheck:` block in the compose file. The app already has a `/login` GET endpoint that returns 200 — this works as a health check target.

---

## Patterns to Follow

### Pattern 1: Environment Variable for All Config

The app currently reads `SECRET_KEY`, `CORS_ALLOWED_ORIGINS`, `FLASK_DEBUG` from `.env` via python-dotenv. Extend this pattern to include `DB_PATH`. The `.env` file is bind-mounted or referenced as `env_file:` in Docker Compose. Never bake secrets into the image.

### Pattern 2: Entrypoint Script for Volume Initialization

The SQLite database must be created before gunicorn starts if it doesn't exist. The current app handles this via `init_db()` called at startup. This pattern continues to work in Docker — on first start with an empty `tennis_data` volume, `init_db()` creates `tennis.db`. On subsequent starts, the existing database is used. Confirm `init_db()` is idempotent (uses `CREATE TABLE IF NOT EXISTS` or checks for existence before creating).

### Pattern 3: Caddy Environment Variable Injection

The Caddyfile supports environment variable expansion with `{$VAR_NAME}` syntax. Use this to avoid hardcoding the domain and DuckDNS token in the Caddyfile:

```
{$DOMAIN} {
    tls {
        dns duckdns {$DUCKDNS_TOKEN}
    }
    ...
}
```

Pass `DOMAIN` and `DUCKDNS_TOKEN` to the Caddy container via `env_file:` or `environment:`.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Multiple Gunicorn Workers

**What:** `--workers 4` or any value above 1 with eventlet
**Why bad:** Flask-SocketIO sessions are in-process memory. Multiple workers = different processes handling the same client's WebSocket vs HTTP requests = "Invalid session" errors and broken real-time updates. The existing systemd config already documents this fix.
**Instead:** Always `--workers 1 --worker-class eventlet`

### Anti-Pattern 2: Bind-Mounting the SQLite File Directly

**What:** `./tennis.db:/app/data/tennis.db` (bind mount to host file)
**Why bad:** File ownership mismatches between host UID and container UID cause read-only database errors. On ARM64 (RPi) the host user UID may differ from x86 dev machines.
**Instead:** Use a named Docker volume for the entire data directory. Initialize the database inside the volume on first run.

### Anti-Pattern 3: Exposing App Port to Host

**What:** Mapping `5000:5000` in the app service
**Why bad:** Bypasses Caddy entirely, exposes unencrypted HTTP to the network
**Instead:** No port mapping on the app service. Only Caddy maps host ports 80 and 443.

### Anti-Pattern 4: Using `caddy:2` Official Image for DuckDNS

**What:** Using the official image without building a custom one
**Why bad:** The official image has no DNS provider modules. DuckDNS DNS-01 challenge will fail silently or fall back to HTTP-01, which may fail if port 80 is blocked.
**Instead:** Build a custom Caddy image with `xcaddy` including `caddy-dns/duckdns`.

### Anti-Pattern 5: Running App Container as Root

**What:** Not adding a non-root USER in the Dockerfile
**Why bad:** If the container is compromised, the attacker has root-equivalent access on the host (Docker without user namespaces). Production security requirement.
**Instead:** Create a dedicated user in the Dockerfile (`RUN useradd -u 1000 appuser`) and switch to it before CMD. Ensure the volume mount directory is owned by this UID.

---

## Scalability Considerations

This is a single-host deployment. No horizontal scaling is in scope. The current architecture supports:

| Concern | At current scale (~45 players) | Notes |
|---------|--------------------------------|-------|
| Concurrent connections | Single eventlet worker handles all via greenlets | Sufficient for club use |
| SQLite write throughput | WAL mode allows concurrent reads, serializes writes | Not a bottleneck for this load |
| Certificate renewal | Caddy handles automatically, no ops needed | Certificates stored in named volume |
| Multi-arch portability | buildx manifest covers RPi (arm64) + x86 server (amd64) | Deploy same image to either |

---

## Sources

- [Flask-SocketIO Deployment — single worker requirement](https://flask-socketio.readthedocs.io/en/latest/deployment.html) — HIGH confidence
- [Caddy reverse_proxy directive — WebSocket support automatic in v2](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy) — HIGH confidence
- [Caddy Automatic HTTPS — DNS-01 challenge](https://caddyserver.com/docs/automatic-https) — HIGH confidence
- [caddy-dns/duckdns module — api_token parameter](https://github.com/caddy-dns/duckdns) — HIGH confidence
- [Docker buildx — multi-platform build](https://docs.docker.com/build/building/multi-platform/) — HIGH confidence
- [Docker Compose networking — service name DNS resolution](https://docs.docker.com/compose/how-tos/networking/) — HIGH confidence
- [Custom Caddy Docker with DNS modules — xcaddy pattern](https://oneuptime.com/blog/post/2026-02-08-how-to-run-caddy-with-docker-and-automatic-https-wildcard-certificates/view) — MEDIUM confidence (verified against Caddy docs)
- [SQLite WAL mode + Docker volume permissions](https://sqlite.org/forum/info/87824f1ed837cdbb) — MEDIUM confidence
- [Docker best practices — non-root user, multi-stage, health checks](https://testdriven.io/blog/docker-best-practices/) — MEDIUM confidence
- Existing deployment: `documentation/99_rpi.txt` — HIGH confidence (working production config)
