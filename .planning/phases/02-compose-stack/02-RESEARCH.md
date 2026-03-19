# Phase 2: Compose Stack - Research

**Researched:** 2026-03-19
**Domain:** Docker Compose v2 + Caddy 2 reverse proxy + SQLite named volumes
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Use official `caddy:2-alpine` image in Phase 2 (plain HTTP reverse proxy, no xcaddy build)
- Caddyfile listens on `:80` (HTTP only, no TLS)
- Include WebSocket header_up directives (Host, X-Real-IP, X-Forwarded-For, X-Forwarded-Proto) from the start
- Caddy exposes port 80 to host (`80:80`); app port 5000 NOT exposed to host
- Caddy uses `depends_on: condition: service_healthy` (app HEALTHCHECK already defined in Dockerfile)
- Named Docker volumes: `tennis_data` at `/app/data`, `caddy_data` for Caddy state
- `restart: unless-stopped` for both services
- `env_file: .env` for the app service
- `.env` stays git-ignored; `.env.example` committed with safe placeholder values
- Phase 2 vars only in `.env.example` (no Phase 3 DuckDNS/ACME placeholders)
- CORS_ALLOWED_ORIGINS dev: `http://192.168.1.8:5000`, production: `https://nechvatal.duckdns.org:10443/`

### Claude's Discretion
- Internal Docker network name
- Caddy log configuration
- Exact docker-compose.yml formatting and comments
- Smoke test approach for volume persistence verification

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| COMP-01 | `docker-compose.yml` defines two services: app and caddy | Docker Compose v2 service syntax, `caddy:2-alpine`, internal bridge network |
| COMP-02 | App and Caddy communicate on an internal bridge network (app port not exposed to host) | Omit `ports` on app service; only Caddy has `80:80`; both share a custom bridge network |
| COMP-03 | SQLite database persisted via named Docker volume mounted at `/app/data` | Named volume `tennis_data` in `volumes:` top-level block, mounted at `/app/data` |
| COMP-04 | `.env.example` documents all configurable environment variables | List all vars the app reads from `.env`: SECRET_KEY, CORS_ALLOWED_ORIGINS, FLASK_DEBUG, FLASK_HOST, FLASK_PORT, TEST_DATE |
</phase_requirements>

---

## Summary

Phase 2 is a straightforward Docker Compose orchestration task with two services: the app container from Phase 1 and an official `caddy:2-alpine` reverse proxy. The technical domain is well-understood and the tools are mature.

All architectural decisions are locked from the CONTEXT.md discussion. The core work is writing three files: `docker-compose.yml`, `Caddyfile`, and `.env.example`. The app container needs no changes — it already binds to `0.0.0.0:5000`, has a HEALTHCHECK, and uses `DB_PATH=/app/data/tennis.db`.

The key insight for COMP-02 is that NOT including a `ports:` block on the app service is all that is needed to keep port 5000 off the host. On a Docker Compose bridge network, services communicate by service name (Docker DNS) without host port mapping. Caddy reaches the app via `reverse_proxy app:5000` on the shared internal network.

**Primary recommendation:** Write a single `docker-compose.yml` that puts both services on a named bridge network, mounts `tennis_data` on the app at `/app/data` and `caddy_data` on Caddy at `/data`, lets Caddy publish `80:80`, and does not publish any port for the app.

---

## Standard Stack

### Core
| Library/Tool | Version | Purpose | Why Standard |
|---|---|---|---|
| `caddy:2-alpine` | 2.11.x (tag `2-alpine` tracks current 2.x) | HTTP reverse proxy, WebSocket passthrough | Official image, minimal footprint, Phase 3 upgrade path to xcaddy |
| Docker Compose v2 | v5.1.0 (confirmed on dev machine) | Multi-container orchestration | Already installed; Compose v2 syntax (`docker compose`) required |

### Supporting
| Feature | Compose Syntax | Purpose | When to Use |
|---|---|---|---|
| Named volumes | `volumes: tennis_data:` + `caddy_data:` at top level | SQLite persistence, Caddy state | Both services need persistent storage |
| `restart: unless-stopped` | per-service | Survive daemon restart / container crash | Both services are long-running |
| `depends_on: condition: service_healthy` | Caddy service | Caddy waits for app HEALTHCHECK before starting | App HEALTHCHECK already defined in Dockerfile |
| `env_file: .env` | app service | Inject secrets into app container | Matches existing `.env` pattern the app already uses |

**Installation:** No new packages. Docker 29.3.0 and Docker Compose v5.1.0 already installed on dev machine.

**Caddy image verified:** `caddy:2-alpine` is pullable (already being pulled). Current Caddy 2.x is 2.11.x as of March 2026. The `2-alpine` tag floats to latest 2.x release — safe for development use.

---

## Architecture Patterns

### File Output
Three new files to create:
```
docker-compose.yml       # project root
Caddyfile                # project root (or caddy/ subdir)
.env.example             # project root, committed to git
```

`.env` already exists and is already `.gitignore`-d.

### Pattern 1: Two-Service Internal Bridge Network

**What:** Both services join a custom bridge network. Caddy publishes port 80 to the host. App publishes nothing — accessible only from within the Docker network by name (`app`).

**When to use:** Any time a reverse proxy fronts a backend that must not be directly reachable from the host.

**Example docker-compose.yml structure:**
```yaml
# Source: Docker Compose official docs + confirmed working pattern
services:
  app:
    build: .
    image: tennis-app:latest
    networks:
      - tennis_net
    volumes:
      - tennis_data:/app/data
    env_file: .env
    restart: unless-stopped
    # No ports: block — port 5000 unreachable from host

  caddy:
    image: caddy:2-alpine
    networks:
      - tennis_net
    ports:
      - "80:80"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
    restart: unless-stopped
    depends_on:
      app:
        condition: service_healthy

networks:
  tennis_net:
    driver: bridge

volumes:
  tennis_data:
  caddy_data:
```

### Pattern 2: Caddyfile for Plain HTTP Reverse Proxy with WebSocket

**What:** Listen on `:80`, proxy to `app:5000` (Docker DNS name of app service on shared network), include ProxyFix-compatible headers.

**Key insight — WebSocket headers in Caddy 2:** Caddy 2's `reverse_proxy` directive **automatically handles WebSocket upgrades** (Connection/Upgrade headers) without explicit directives. The `header_up` block in the locked decisions (Host, X-Real-IP, X-Forwarded-For, X-Forwarded-Proto) is still correct to include for the Flask `ProxyFix` middleware — these are standard forwarded-header directives, not WebSocket-specific.

**Source:** Official Caddy docs state: "The proxy also supports WebSocket connections, performing the HTTP upgrade request then transitioning the connection to a bidirectional tunnel." No additional header_up needed for WS upgrade itself.

```
# Source: Caddyserver.com docs + existing RPi Caddyfile pattern (documentation/99_rpi.txt)
:80 {
    reverse_proxy app:5000 {
        header_up Host {http.request.host}
        header_up X-Real-IP {http.request.remote}
        header_up X-Forwarded-For {http.request.remote}
        header_up X-Forwarded-Proto {http.request.scheme}
    }
}
```

**Why `:80` not a domain:** Phase 2 is local HTTP only, no domain name yet. Domain-based config is Phase 3.

### Pattern 3: Named Volume Prevents Host Permission Issues

**What:** Use `tennis_data:` named volume (not `./data:/app/data` bind mount). Docker manages the volume with appropriate permissions.

**Why:** The app runs as UID/GID 1000 (`appuser`). On a bind mount, the host directory may be owned by a different UID, causing `Permission denied` on SQLite writes. Named volumes are created by Docker and owned by the first process that writes them (the container), avoiding host UID mismatch. This was decided in Phase 1.

**Persistence behavior:**
- `docker compose down` — containers removed, volumes SURVIVE
- `docker compose down -v` — containers AND volumes removed (data lost)

### Anti-Patterns to Avoid

- **Bind-mounting SQLite data directory:** `./data:/app/data` will cause UID permission errors if host UID != 1000 (appuser). Use named volume.
- **Exposing app port to host:** Adding `ports: - "5000:5000"` to app service defeats COMP-02. Keep app port internal only.
- **Using `depends_on` without condition:** Plain `depends_on: [app]` only waits for container start, not app readiness. Use `condition: service_healthy` to leverage the Dockerfile HEALTHCHECK.
- **Putting Caddyfile inline:** Bind-mounting `./Caddyfile:/etc/caddy/Caddyfile:ro` is correct. Do not attempt to bake the Caddyfile into the image in Phase 2.
- **Phase 3 Caddyfile config in Phase 2:** `:80` listener with no domain, no `tls` block. Phase 3 will replace Caddyfile entirely.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| WebSocket header forwarding | Custom nginx/proxy conf | Caddy `reverse_proxy` | Caddy 2 handles WS upgrade automatically |
| Service startup ordering | Shell sleep loops | `depends_on: condition: service_healthy` | Uses existing Dockerfile HEALTHCHECK |
| SQLite permission management | chmod scripts, entrypoint hacks | Named Docker volumes | Docker handles ownership; Phase 1 already sets `/app/data` permissions correctly |
| Environment variable injection | Baking vars into image | `env_file: .env` in compose | Standard pattern; keeps secrets out of image |

---

## Common Pitfalls

### Pitfall 1: `depends_on: condition: service_healthy` Requires HEALTHCHECK on Dependency
**What goes wrong:** Docker Compose silently fails or throws error "service_healthy but no healthcheck defined" if the dependency (app) has no HEALTHCHECK.
**Why it happens:** `condition: service_healthy` consults the health status reported by Docker, which requires a HEALTHCHECK instruction in the Dockerfile.
**How to avoid:** The Phase 1 Dockerfile already has the HEALTHCHECK (`/health` endpoint, interval=30s, start-period=15s). No action needed.
**Warning signs:** `compose up` error: "service 'caddy' depends on service 'app' which is undefined."

### Pitfall 2: App Healthcheck Start-Period vs. Compose Timing
**What goes wrong:** Caddy fails to start because app health check hasn't passed yet (start-period=15s means Docker waits 15s before marking unhealthy, but "healthy" state is only reached after the first successful check).
**Why it happens:** HEALTHCHECK with `--start-period=15s --interval=30s` means the first health check runs ~15s after startup. App must be serving `/health` within that window.
**How to avoid:** Gunicorn/eventlet startup is fast (~2-3s). The 15s start period is sufficient. If startup is slow, health check will eventually pass and Caddy will start.
**Warning signs:** Caddy container stays in "waiting" state for >60s.

### Pitfall 3: Caddy Auto-HTTPS Attempting TLS on `:80`
**What goes wrong:** If the Caddyfile has a bare domain name (e.g., `localhost` or an IP), Caddy 2 may attempt to obtain TLS certificates.
**Why it happens:** Caddy 2's automatic HTTPS feature activates for any site address that isn't an explicit IP/port combo.
**How to avoid:** Use `:80` as the site address (not `localhost:80` or a domain). The `:80` syntax explicitly disables automatic HTTPS in Caddy.
**Warning signs:** Caddy logs show ACME certificate requests; port 443 bind attempts.

### Pitfall 4: `docker compose up` Doesn't Rebuild Image
**What goes wrong:** App code changes aren't reflected after `docker compose up` because the existing image is reused.
**Why it happens:** Compose only pulls/rebuilds if explicitly told to.
**How to avoid:** Use `docker compose up --build` when iterating. For smoke test, build explicitly first: `docker build -t tennis-app:latest .` then `docker compose up -d`.
**Warning signs:** Old app version running inside container.

### Pitfall 5: `.env` Not Present on Fresh Clone
**What goes wrong:** `docker compose up` fails with error because `env_file: .env` is specified but `.env` doesn't exist.
**Why it happens:** `.env` is git-ignored; only `.env.example` is committed.
**How to avoid:** `.env.example` instructions (or a README note) must tell the operator to `cp .env.example .env` and fill in secrets before first run.
**Warning signs:** `docker compose up` error: "env file .env does not exist".

---

## Code Examples

Verified patterns from official sources:

### Complete docker-compose.yml
```yaml
# Source: Docker Compose v2 spec (docs.docker.com/compose)
# Phase 2: App + Caddy plain HTTP stack
services:
  app:
    build: .
    image: tennis-app:latest
    networks:
      - tennis_net
    volumes:
      - tennis_data:/app/data
    env_file: .env
    restart: unless-stopped
    # No ports: — port 5000 only reachable inside Docker network (COMP-02)

  caddy:
    image: caddy:2-alpine
    networks:
      - tennis_net
    ports:
      - "80:80"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
    restart: unless-stopped
    depends_on:
      app:
        condition: service_healthy

networks:
  tennis_net:
    driver: bridge

volumes:
  tennis_data:   # SQLite persistence — survives compose down (COMP-03)
  caddy_data:    # Caddy state — needed for Phase 3 TLS certs
```

### Complete Caddyfile
```
# Source: caddyserver.com/docs + existing RPi pattern (documentation/99_rpi.txt)
# Phase 2: Plain HTTP reverse proxy — no TLS (Phase 3 adds DuckDNS ACME)
:80 {
    log {
        output stderr
        level ERROR
    }

    reverse_proxy app:5000 {
        header_up Host              {http.request.host}
        header_up X-Real-IP        {http.request.remote}
        header_up X-Forwarded-For  {http.request.remote}
        header_up X-Forwarded-Proto {http.request.scheme}
    }
}
```

### .env.example
```bash
# Source: Existing .env pattern + app.py env var list (CLAUDE.md)
# Copy to .env and fill in real values before running docker compose up

# REQUIRED: Flask session encryption key — generate with: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=change-me-generate-a-real-secret

# REQUIRED: CORS allowed origins (comma-separated)
# Development (direct access): CORS_ALLOWED_ORIGINS=http://192.168.1.8:5000
# Production (via Caddy/DuckDNS): CORS_ALLOWED_ORIGINS=https://nechvatal.duckdns.org:10443/
CORS_ALLOWED_ORIGINS=http://localhost:80

# Optional: Enable Flask debug mode (set false in production)
FLASK_DEBUG=false

# Optional: Override system time for testing (format: YYYY-MM-DD-HH-MM-SS)
# TEST_DATE=2025-01-15-10-00-00
```

### Volume Persistence Smoke Test (manual)
```bash
# Source: Docker Compose docs (docker.com/compose/how-tos/networking)
# Verify COMP-03: data survives docker compose down/up

# 1. Start stack
docker compose up -d

# 2. Create a challenge or change player data (via browser at http://localhost)

# 3. Stop stack (volumes survive)
docker compose down

# 4. Restart stack
docker compose up -d

# 5. Verify data still exists at http://localhost
```

### Verify App Not Reachable Directly (COMP-02 check)
```bash
# Should succeed (via Caddy):
curl -s http://localhost/health

# Should fail — connection refused (port 5000 not published to host):
curl -s http://localhost:5000/health
# Expected: curl: (7) Failed to connect to localhost port 5000: Connection refused
```

---

## State of the Art

| Old Approach | Current Approach | Impact for This Phase |
|---|---|---|
| `docker-compose` (v1, Python) | `docker compose` (v2, Go plugin) | Use `docker compose` command; v1 syntax is same but v2 is installed |
| `version:` key in compose file | Key deprecated/ignored in Compose v2 | Omit `version:` key entirely — Compose v2 ignores it and may warn |
| Manual WebSocket header forwarding | Caddy 2 handles WS upgrade automatically | `header_up` for ProxyFix headers only; no Connection/Upgrade header_up needed |
| Bind mounts for SQLite | Named volumes | Named volumes for correct permissions with non-root container user |

**Deprecated/outdated:**
- `version: "3.9"` in docker-compose.yml: The `version` top-level key is deprecated in Compose v2 (the spec no longer requires it). Omit it to avoid deprecation warnings.
- `docker-compose` (v1 binary): The project uses `docker compose` v5.1.0 (v2 plugin). Use the two-word command.

---

## Open Questions

1. **`build:` vs pre-built image in compose**
   - What we know: `docker-compose.yml` can use `build: .` to build the image OR `image: tennis-app:latest` to use a pre-built one.
   - What's unclear: Whether the planner should specify `build: .` (convenience for dev) or `image:` only (forces explicit build step).
   - Recommendation: Use both (`build: .` + `image: tennis-app:latest`) — `build:` provides a fallback if image doesn't exist locally; `image:` names the resulting image for later reference. This is common practice.

2. **Caddy log output destination**
   - What we know: Caddy supports `output file`, `output stderr`, `output stdout`.
   - What's unclear: `output stderr` routes to `docker logs caddy` (stderr stream); `output stdout` to stdout stream. Either works for `docker logs`.
   - Recommendation: Use `output stderr` at `level ERROR` to minimize noise in `docker logs` while keeping error visibility. This matches the RPi Caddyfile intent.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing, pytest.ini present) |
| Config file | `pytest.ini` (testpaths = tests) |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map

Phase 2 requirements are integration/smoke tests that require a running Docker stack. They cannot be automated as pytest unit tests. All four COMP requirements are verified manually.

| Req ID | Behavior | Test Type | Automated Command | Notes |
|--------|----------|-----------|-------------------|-------|
| COMP-01 | `docker compose up -d` starts both services without error | smoke | `docker compose up -d && docker compose ps` | Manual verification; both services show "Up"/"healthy" |
| COMP-02 | App port 5000 not reachable from host; port 80 reaches app via Caddy | smoke | `curl http://localhost/health` succeeds; `curl http://localhost:5000/health` fails | Manual two-command check |
| COMP-03 | Data survives `docker compose down && docker compose up -d` | smoke | Manual: create data, down, up, verify | Cannot automate without test fixtures inside running container |
| COMP-04 | `.env.example` documents all env vars | review | `cat .env.example` | Manual review against CLAUDE.md env var list |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q` (existing unit tests; verify nothing regressed in Python code)
- **Per wave merge:** Full docker smoke test sequence (COMP-01 through COMP-04 manual checks)
- **Phase gate:** Full smoke test green before `/gsd:verify-work`

### Wave 0 Gaps
None — existing test infrastructure covers Phase 1 unit tests. Phase 2 tests are smoke/integration tests performed manually during plan execution, not new pytest files.

---

## Sources

### Primary (HIGH confidence)
- Docker Compose official docs (docs.docker.com/compose/how-tos/networking/) — networking model, named volumes, `depends_on` conditions
- Caddy official docs (caddyserver.com/docs/caddyfile/directives/reverse_proxy) — WebSocket automatic handling, `header_up` syntax
- Existing project files (Dockerfile, entrypoint.sh, documentation/99_rpi.txt) — Phase 1 outputs and production Caddy patterns
- `docker compose version` output on dev machine — v5.1.0 confirmed

### Secondary (MEDIUM confidence)
- Docker Hub caddy tags page — caddy:2-alpine confirmed pullable, current 2.x = 2.11.x
- docker.recipes/web-servers/caddy-reverse-proxy — compose structure with `caddy_data` and `caddy_config` volumes, internal bridge network pattern
- caddy.community/t/setting-up-websocket-communication-with-caddy/26041 — confirms no explicit WS upgrade headers needed in Caddy 2

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — caddy:2-alpine confirmed pullable; Docker Compose v5.1.0 confirmed installed; all decisions locked
- Architecture: HIGH — patterns verified against official Docker Compose and Caddy docs; existing RPi Caddyfile cross-referenced
- Pitfalls: HIGH — based on official docs behavior (HEALTHCHECK requirement for service_healthy, Caddy auto-HTTPS on domain names)

**Research date:** 2026-03-19
**Valid until:** 2026-04-19 (stable ecosystem; Caddy 2.x and Compose v2 are mature)
