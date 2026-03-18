# Domain Pitfalls: Docker Deployment of Flask+SQLite+Caddy

**Domain:** Containerized Flask-SocketIO app with SQLite persistence and Caddy reverse proxy
**Researched:** 2026-03-18
**Confidence:** HIGH (most pitfalls verified via official docs, issue trackers, and multiple sources)

---

## Critical Pitfalls

Mistakes that cause rewrites, data loss, or outages.

---

### Pitfall 1: SQLite Volume Permissions Break on Non-Root Container User

**What goes wrong:** The container runs as a non-root user (correct security practice), but the Docker volume directory is initialized owned by root (UID 0). SQLite cannot open the database file for writing. Error: `attempt to write a readonly database` or `OperationalError: unable to open database file`.

**Why it happens:** Docker named volumes initialize with the directory owned by root unless the Dockerfile explicitly `chown`s the directory before the `USER` instruction. Bind mounts inherit host filesystem ownership, which frequently does not match the container's user UID.

**Consequences:** App starts but crashes on first database write. If using named volumes and the image was previously run as root, the volume ownership must be manually corrected on the host — a painful production incident.

**Prevention:**
- In the Dockerfile, create the data directory and set ownership before switching to the non-root user:
  ```dockerfile
  RUN mkdir -p /app/data && chown -R appuser:appuser /app/data
  USER appuser
  ```
- For bind mounts (host path), ensure the host directory is owned by the same UID the container uses (e.g., UID 1000). Set this explicitly in Compose:
  ```yaml
  volumes:
    - ./data:/app/data
  ```
  And pre-create the host directory: `mkdir -p ./data && chown 1000:1000 ./data`
- Prefer named volumes over bind mounts for SQLite — Docker copies the image directory permissions into an empty named volume on first run, so if the Dockerfile owns the directory correctly, it works automatically.

**Detection (warning signs):**
- `OperationalError` or `unable to open database` in container logs at startup
- `ls -la` on the volume shows `root` ownership while container `whoami` is non-root
- App works in dev (where you ran as root) but fails in production (non-root user configured)

**Phase:** Dockerfile and Docker Compose setup phase (Day 1)

---

### Pitfall 2: SQLite WAL Mode Fails on Network Filesystems

**What goes wrong:** WAL (Write-Ahead Logging) mode requires all processes accessing the database to share memory via mmap. This works on local filesystems but silently fails or corrupts data on network-mounted filesystems (NFS, CIFS/SMB, FUSE-based network mounts).

**Why it happens:** WAL creates two auxiliary files (`-wal` and `-shm`). The `-shm` file is a shared memory file that requires POSIX shared memory semantics. Network filesystems typically do not provide these semantics.

**Consequences:** Database corruption, `SQLITE_PROTOCOL` errors, or silent data loss. This is a rare but catastrophic edge case. The app runs fine locally (local Docker volume) but fails if the volume is ever moved to network-attached storage.

**Prevention:**
- Always use local Docker volumes or bind mounts on local filesystem for SQLite
- Never mount an SQLite database from NFS, CIFS, or any network filesystem
- Document this constraint in the deployment README
- If network storage is ever needed, consider SQLite-incompatible use case requiring PostgreSQL migration

**Detection (warning signs):**
- Deployment on a NAS or network-backed storage
- `SQLITE_IOERR_LOCK` errors in logs
- WAL checkpoint never completes

**Phase:** Infrastructure/deployment decisions (pre-build)

---

### Pitfall 3: Gunicorn Multi-Worker Breaks SocketIO (Silent Failure)

**What goes wrong:** Running gunicorn with more than 1 worker causes Socket.IO connections to fail randomly. A client connects to worker A, but subsequent polling or WebSocket frames are load-balanced to worker B. Worker B has no memory of that client's session. The client appears "disconnected" to the server but still shows "connected" on the client side.

**Why it happens:** Flask-SocketIO uses in-process state (the eventlet async loop) to track connected clients. With multiple workers, each process has independent state. Without a message queue (Redis) as a backend, cross-worker communication is impossible. The Flask-SocketIO docs explicitly state: "it is not possible to use more than one worker process when using this web server" (for gunicorn without a message queue).

**Consequences:** Real-time updates stop working for some users. Ranking changes are not broadcast to all clients. Symptoms are intermittent and hard to debug because they depend on which worker handles each request.

**Prevention:**
- Hard-code `--workers 1` in the gunicorn command:
  ```
  gunicorn wsgi:app --bind 0.0.0.0:5000 --worker-class eventlet --workers 1
  ```
- Add this as a comment in the Dockerfile CMD and in documentation so no one "optimizes" it later
- Do NOT use `--worker-class eventlet --workers $(nproc)` — the nproc shortcut is dangerous here

**Detection (warning signs):**
- Real-time updates only reach some connected users
- Socket.IO events fire on the server but clients show stale data
- `ERR_CONNECTION_RESET` on WebSocket connections intermittently

**Phase:** Dockerfile CMD / gunicorn configuration (Day 1)

---

### Pitfall 4: Eventlet Monkey Patching Must Happen Before All Other Imports

**What goes wrong:** Eventlet's monkey patching (`eventlet.monkey_patch()`) rewrites the standard library's socket, threading, and time modules with async-compatible greenlet versions. If any module imports `socket` or `threading` before the monkey patch runs, those modules get the original blocking versions. This creates a "split brain" — some code paths block the entire eventlet loop.

**Why it happens:** In a Flask app, `app.py` imports many things at module level. If monkey patching is not the absolute first code to run, modules like `bcrypt`, `ssl`, or database connectors can grab the blocking socket. In Docker, the interpreter startup path may differ from the development setup.

**Consequences:** Periodic server hangs where no requests are accepted. WebSocket connections freeze after some idle time. Difficult to reproduce (timing-dependent). The known Docker-specific symptom: a 60-second hang at startup before any events are received.

**Prevention:**
- Monkey patch must be at the very top of the entry point (before any other import):
  ```python
  import eventlet
  eventlet.monkey_patch()
  # Only then: from flask import Flask, etc.
  ```
- For gunicorn with eventlet worker class, gunicorn handles the monkey patch automatically — do not call `monkey_patch()` manually when using `--worker-class eventlet`
- Verify entry point ordering in both `app.py` and any `wsgi.py` wrapper

**Detection (warning signs):**
- Intermittent freezes with no error logs
- 60-second delay before first WebSocket event in Docker
- Works fine locally but hangs under gunicorn in container

**Phase:** Dockerfile and wsgi entry point configuration (Day 1)

---

### Pitfall 5: Eventlet Is in Maintenance Mode — Compatibility Risk With Python 3.12

**What goes wrong:** The project uses Python 3.12 and eventlet. Eventlet is officially in maintenance mode ("life support") as of 2024/2025. Compatibility with Python 3.10+ has historically lagged, and Python 3.12 introduced changes (removal of deprecated `asynchat`, `asyncore`, changes to `ssl`) that broke eventlet in prior versions.

**Why it happens:** Eventlet relied on internal CPython details that have been removed or changed. The eventlet project has minimal active maintainers.

**Consequences:** The Docker build may succeed but the container crashes at runtime when eventlet tries to monkey-patch modules that no longer exist in Python 3.12. Or subtle async bugs appear only under load.

**Prevention:**
- Pin both `eventlet` and `Flask-SocketIO` to known-compatible versions in `requirements.txt` (or `prod-requirements.txt`). Do not use unpinned `eventlet` or `flask-socketio` — an update may silently break Python 3.12 compatibility.
- Test the container with `docker run ... python -c "import eventlet; eventlet.monkey_patch(); print('OK')"` as a smoke test before full deployment.
- Consider migrating to `gevent` as the async backend (more actively maintained, similar API) if eventlet causes stability issues.

**Detection (warning signs):**
- `ImportError` or `AttributeError` on eventlet import in Python 3.12
- Gunicorn worker boot failures with eventlet worker class
- Runtime errors referencing `asyncore` or `asynchat` (removed in Python 3.12)

**Phase:** Dockerfile base image and requirements pinning (Day 1)

---

### Pitfall 6: Let's Encrypt Rate Limits During Caddy Configuration Iteration

**What goes wrong:** While testing the Caddy + DuckDNS HTTPS configuration, repeatedly restarting the Caddy container triggers new ACME certificate requests. Let's Encrypt enforces 5 failed validations per hour per domain and 50 certificates per domain per week. Hitting these limits locks out the domain from new certificates for up to 7 days.

**Why it happens:** Each time Caddy starts fresh (deleted volume, new config, container restart), it may attempt a new certificate issuance. If the DuckDNS token is wrong, the DNS-01 challenge fails repeatedly, consuming rate-limit quota.

**Consequences:** HTTPS stops working for the domain for up to a week. During the lockout, only HTTP is available. This can block the entire milestone if it happens during final testing.

**Prevention:**
- During development and testing, use the Let's Encrypt **staging** ACME endpoint in Caddyfile:
  ```
  acme_ca https://acme-staging-v02.api.letsencrypt.org/directory
  ```
  Only switch to production endpoint after confirming DNS-01 challenge works correctly.
- Persist the Caddy data volume (`caddy_data`) across restarts so Caddy reuses existing certificates instead of re-requesting.
- Verify the DuckDNS token works before touching Caddy: `curl "https://www.duckdns.org/update?domains=YOURDOMAIN&token=YOUR_TOKEN&ip="`

**Detection (warning signs):**
- `rateLimited` error in Caddy logs
- `urn:ietf:params:acme:error:rateLimited` in ACME response
- Caddy logs show repeated certificate request failures

**Phase:** Caddy + DuckDNS HTTPS configuration phase (do staging tests first)

---

## Moderate Pitfalls

---

### Pitfall 7: Caddy Does Not Automatically Handle Socket.IO's Polling-to-WebSocket Upgrade

**What goes wrong:** Flask-SocketIO (with Socket.IO client) starts connections with HTTP long-polling and then upgrades to WebSocket. This upgrade requires the reverse proxy to correctly pass the `Connection: Upgrade` and `Upgrade: websocket` headers. If Caddy drops or rewrites these headers, clients stay on polling mode and never upgrade. The app works but is slower and more resource-intensive than necessary.

**Why it happens:** Caddy v2 handles WebSocket proxying transparently without special configuration, but only for connections on the standard `reverse_proxy` block. If the Caddyfile has custom header manipulation (e.g., `header_down` or `header_up` directives that strip `Connection`), the upgrade can break.

**Additional issue:** Socket.IO uses sticky sessions implicitly — the polling transport requires all requests in a session to hit the same backend. With a single gunicorn worker (as required), this is not a problem. But if load balancing is ever added, sticky sessions must be configured.

**Consequences:** Clients fall back to HTTP polling. Real-time updates are delayed and server load increases. May not be immediately obvious without checking the browser network tab.

**Prevention:**
- Keep the Caddyfile minimal — do not add header stripping rules unless necessary
- A working minimal Caddyfile for this setup:
  ```
  yourdomain.duckdns.org {
      reverse_proxy app:5000
  }
  ```
  Caddy v2 handles WebSocket upgrade automatically with this.
- Test WebSocket upgrade explicitly: in browser devtools, verify the `/socket.io/` request shows `101 Switching Protocols` status (not `200 OK` with polling).

**Detection (warning signs):**
- Browser devtools shows repeated `GET /socket.io/?transport=polling` with no `101` response
- Client-side Socket.IO logs show `transport: polling` after connection established
- Higher than expected server CPU from polling overhead

**Phase:** Caddy configuration and integration testing

---

### Pitfall 8: Multi-Arch Build Fails for ARM64 Due to Missing C Compiler

**What goes wrong:** Building for `linux/arm64` via QEMU emulation on an x86 machine, some Python packages (potentially `bcrypt`, `greenlet` for eventlet) do not have prebuilt `manylinux` wheels for ARM64. pip falls back to building from source, which requires `gcc`, `python3-dev`, and other build tools — not present in `python:3.12-slim`.

**Why it happens:** The `slim` Docker images omit build tools. QEMU emulation makes ARM64 source compilation very slow (5-10x slower than native). Packages like `greenlet` (required by eventlet) require C compilation.

**Consequences:** Build succeeds on x86 but fails on ARM64 with `gcc not found` or `error: command 'gcc' failed`. Or the build appears to succeed but crashes on the Pi because a wrong-architecture binary was silently included.

**Prevention:**
- In the build stage of the multi-stage Dockerfile, use `python:3.12-bookworm` (not slim) or explicitly install build dependencies:
  ```dockerfile
  FROM python:3.12-slim AS builder
  RUN apt-get update && apt-get install -y --no-install-recommends gcc python3-dev libffi-dev && rm -rf /var/lib/apt/lists/*
  ```
- Pre-compile all wheels in the builder stage, then copy only the wheels to the slim runtime stage
- Test the ARM64 build explicitly: `docker buildx build --platform linux/arm64 --load -t app:test .` (requires QEMU on the build host)
- Alternatively, build natively on the Pi itself for the ARM64 image — slower but no QEMU needed

**Detection (warning signs):**
- `error: command 'gcc' failed with exit code 1` during `pip install` in Docker build
- Build succeeds on developer machine (x86) but fails in `--platform linux/arm64` mode
- `exec format error` when running the container on the Pi (wrong arch binary sneaked in)

**Phase:** Dockerfile multi-stage and multi-arch build phase

---

### Pitfall 9: SECRET_KEY and DuckDNS Token Exposed in Docker Inspect

**What goes wrong:** Secrets passed as environment variables (`-e SECRET_KEY=...` or in `docker-compose.yml` `environment:` block) are visible in plaintext via `docker inspect <container>`. On a shared or compromised host, this leaks the Flask session key and the DuckDNS API token.

**Why it happens:** Environment variables are stored unencrypted in the container runtime metadata. This is a fundamental Docker design characteristic, not a misconfiguration.

**Consequences:** Compromised `SECRET_KEY` allows session forgery and authentication bypass. Leaked DuckDNS token allows an attacker to update DNS records, potentially redirecting the domain.

**Prevention:**
- Use a `.env` file that is **not committed to git** (add `.env` to `.gitignore`). Docker Compose reads `.env` automatically.
- Add `.env.example` with placeholder values to the repo for documentation.
- For a single-host deployment, a `.env` file provides reasonable security (requires host access to read).
- For higher security: use Docker secrets (Swarm feature) or a secrets manager — but for this single-Pi deployment, `.env` file is an acceptable tradeoff.
- The existing codebase already has a weak default `SECRET_KEY` — the Docker setup must enforce that `SECRET_KEY` is set and is strong (at least 32 random bytes). Add an assertion in app startup.

**Detection (warning signs):**
- `docker inspect <container>` shows secrets in plaintext `Env` array
- `.env` file committed to git (check `git log --all --full-history -- .env`)
- Weak or default `SECRET_KEY` in production logs

**Phase:** Environment configuration phase (`.env` setup)

---

### Pitfall 10: Large requirements.txt Bloats the Docker Image and Slows Builds

**What goes wrong:** The existing `requirements.txt` contains 150+ packages including development tools (`black`, `flake8`, `pytest`, `ipython`, `mypy`). Installing all of these in the production Docker image adds hundreds of MB and minutes to build time, especially under QEMU emulation for ARM64.

**Why it happens:** The full development requirements were used for the existing setup. A `prod-requirements.txt` exists but may be incomplete or not used in the Docker build.

**Consequences:** Image size balloons (potentially 1GB+). Build time on ARM64 via QEMU is extremely slow. Larger attack surface (more installed packages = more potential CVEs). Slower container startup.

**Prevention:**
- Use `prod-requirements.txt` (already exists) in the Dockerfile. Audit it to ensure it contains only runtime dependencies.
- Multi-stage build: install into a virtualenv in the builder stage, copy only the virtualenv to the runtime stage — dev tools never enter the final image.
- Add `--no-cache-dir` to pip install to avoid pip's cache bloating the layer.
- Copy `requirements` files before application code so Docker layer cache is reused when only code changes:
  ```dockerfile
  COPY prod-requirements.txt .
  RUN pip install --no-cache-dir -r prod-requirements.txt
  COPY . .  # This layer invalidated on every code change, pip install is not
  ```

**Detection (warning signs):**
- Docker image size over 500MB for a simple Flask app
- `docker build` takes more than 5 minutes on ARM64
- `pip list` in the container shows pytest, black, or other dev tools

**Phase:** Dockerfile construction phase

---

## Minor Pitfalls

---

### Pitfall 11: Caddy Data Volume Not Persisted — Certificates Lost on Restart

**What goes wrong:** If the `caddy_data` volume is not defined in Docker Compose, Caddy stores its certificates inside the container filesystem. Every time the container is recreated (image rebuild, update), the certificate is gone and Caddy re-requests from Let's Encrypt. This increases rate-limit consumption and adds startup delay.

**Prevention:**
- Always define and mount a persistent volume for Caddy's data directory:
  ```yaml
  volumes:
    caddy_data:
      external: false
  services:
    caddy:
      volumes:
        - caddy_data:/data
        - caddy_config:/config
  ```
- Similarly persist `/config` for Caddy's runtime configuration.

**Detection:** Caddy requests a new certificate every time it starts.

**Phase:** Docker Compose configuration

---

### Pitfall 12: Container Does Not Handle SIGTERM Gracefully — SocketIO Clients Drop Hard

**What goes wrong:** When `docker stop` is issued (or during a deployment update), Docker sends SIGTERM to PID 1 in the container. If the entrypoint is a shell script (not the Python process itself) or gunicorn's shutdown timeout is too short, active WebSocket connections are dropped abruptly without the Socket.IO disconnect event firing.

**Why it happens:** Default `docker stop` timeout is 10 seconds, then SIGKILL. Gunicorn needs time to drain connections. Shell script entrypoints may not forward signals to the child process.

**Consequences:** Connected clients show "disconnected" without cleanup. Any in-flight database writes may be incomplete.

**Prevention:**
- Use `exec` in shell entrypoints to replace the shell process with gunicorn (so gunicorn is PID 1 and receives signals directly):
  ```sh
  exec gunicorn wsgi:app ...
  ```
- Or use `CMD ["gunicorn", "wsgi:app", ...]` (list form) in Dockerfile — this runs gunicorn directly as PID 1 without a shell.
- Set `stop_grace_period: 30s` in Docker Compose for the app service to give gunicorn time to drain.

**Detection:** `docker stop` is immediate (no graceful shutdown messages from gunicorn in logs).

**Phase:** Dockerfile CMD / entrypoint configuration

---

### Pitfall 13: Health Check Endpoint Returns 200 But App Is Broken

**What goes wrong:** The Docker health check (`HEALTHCHECK` in Dockerfile or `healthcheck:` in Compose) pings a simple endpoint that returns 200 even when the database is unreadable, gunicorn workers have crashed, or Socket.IO is not initialized.

**Prevention:**
- Make the health check endpoint verify actual app state (e.g., do a read query from SQLite):
  ```python
  @app.route('/health')
  def health():
      try:
          db = get_db()
          db.execute('SELECT 1')
          return {'status': 'ok'}, 200
      except Exception as e:
          return {'status': 'error', 'detail': str(e)}, 500
  ```
- The Dockerfile health check should use this meaningful endpoint.

**Detection:** Container shows "healthy" but login fails or rankings don't load.

**Phase:** Health check implementation phase

---

### Pitfall 14: Bind Mount Includes .git, __pycache__, and .env in Container

**What goes wrong:** If development uses a bind mount of the entire project directory (convenient for local dev), or if `.dockerignore` is incomplete, the Docker build context includes `.git/` (large), `__pycache__/` (pollutes the image), and `.env` (sensitive secrets baked into the image layer).

**Prevention:**
- Create a comprehensive `.dockerignore` before the first build:
  ```
  .git
  .gitignore
  __pycache__
  *.pyc
  *.pyo
  .env
  .venv
  venv
  *.db
  *.db-wal
  *.db-shm
  documentation
  .planning
  tests
  ```
- Note: the SQLite database itself (`.db` file) should NOT be baked into the image — it lives on the volume.

**Detection:**
- Build context is very large (check `docker build` output: "Sending build context to Docker daemon X MB")
- `docker run ... ls /app` shows `.git/` directory
- `.env` appears in `docker history <image>`

**Phase:** Dockerfile and .dockerignore setup (Day 1)

---

## Phase-Specific Warnings

| Phase | Likely Pitfall | Mitigation |
|-------|---------------|------------|
| Dockerfile creation | Non-root user + volume permission mismatch (Pitfall 1) | Create and chown data dir before USER instruction |
| Dockerfile creation | Bloated image from dev requirements (Pitfall 10) | Use prod-requirements.txt; multi-stage build |
| Dockerfile creation | ARM64 build fails due to missing gcc (Pitfall 8) | Install build tools in builder stage only |
| Dockerfile CMD | Multiple gunicorn workers break SocketIO (Pitfall 3) | Hard-code `--workers 1` with comment |
| Dockerfile CMD | Shell entrypoint swallows SIGTERM (Pitfall 12) | Use `exec` or list-form CMD |
| Dockerfile CMD | Eventlet monkey patch ordering (Pitfall 4) | Verify import order; let gunicorn handle patching |
| .dockerignore | Secrets and database baked into image (Pitfall 14) | Comprehensive .dockerignore before first build |
| Docker Compose | Caddy data volume not persisted (Pitfall 11) | Define named volumes for caddy_data and caddy_config |
| Environment config | Secrets visible in docker inspect (Pitfall 9) | .env file not in git; assert SECRET_KEY is set |
| Caddy HTTPS setup | Let's Encrypt rate limit during iteration (Pitfall 6) | Use staging ACME endpoint during testing |
| Caddy HTTPS setup | WebSocket upgrade not passing through (Pitfall 7) | Minimal Caddyfile; verify 101 in browser devtools |
| Python 3.12 + eventlet | Eventlet incompatibility at runtime (Pitfall 5) | Pin versions; smoke-test monkey patch in container |
| Integration testing | SQLite WAL on wrong filesystem (Pitfall 2) | Document: local filesystem volumes only |
| Health check | Health endpoint lies (Pitfall 13) | Health endpoint must query the database |

---

## Sources

- [Flask-SocketIO Deployment Docs — Single Worker Requirement](https://flask-socketio.readthedocs.io/en/stable/deployment.html)
- [Flask-SocketIO Issue #924 — Eventlet Workers Limit](https://github.com/miguelgrinberg/Flask-SocketIO/issues/924)
- [Flask-SocketIO Discussion #1915 — Eventlet vs Gevent Status](https://github.com/miguelgrinberg/Flask-SocketIO/discussions/1915)
- [Flask-SocketIO Issue #1385 — 60s Docker Hang with Eventlet](https://github.com/miguelgrinberg/Flask-SocketIO/issues/1385)
- [SQLite Write-Ahead Logging — Official Docs (WAL and network FS warning)](https://www.sqlite.org/wal.html)
- [SQLite Forum — WAL and SHM Permissions in Docker Compose](https://sqlite.org/forum/info/87824f1ed837cdbb)
- [Docker Docs — Manage Sensitive Data with Docker Secrets](https://docs.docker.com/engine/swarm/secrets/)
- [Caddy Docs — Automatic HTTPS (rate limits, staging)](https://caddyserver.com/docs/automatic-https)
- [Caddy Community — Rate Limited by Let's Encrypt](https://caddy.community/t/caddy-ratelimited-by-letsencrypt/710)
- [caddy-dns/duckdns GitHub — DuckDNS Module for Caddy](https://github.com/caddy-dns/duckdns)
- [Caddy Docs — reverse_proxy directive (WebSocket headers)](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy)
- [Docker Forums — Non-Root User + Volume Mount Permissions](https://forums.docker.com/t/how-to-mount-a-docker-volume-so-as-writeable-by-a-non-root-user-within-the-container/144321)
- [TestDriven.io — Docker Best Practices for Python Developers](https://testdriven.io/blog/docker-best-practices/)
- [Python Speed — Multi-Stage Docker Python Specifics](https://pythonspeed.com/articles/multi-stage-docker-python/)
- [OneUptime — Debug Docker Multi-Platform Build Issues](https://oneuptime.com/blog/post/2026-01-25-debug-docker-multi-platform-build-issues/view)
- [OneUptime — How to Run SQLite in Docker](https://oneuptime.com/blog/post/2026-02-08-how-to-run-sqlite-in-docker-when-and-how/view)
- [Security Boulevard — Environment Variables and Secrets in 2026](https://securityboulevard.com/2025/12/are-environment-variables-still-safe-for-secrets-in-2026/)
