# Phase 4: Multi-Arch & RPi Deploy - Context

**Gathered:** 2026-03-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Build multi-architecture Docker images (AMD64 + ARM64) for both the app and custom Caddy containers, push them to GitHub Container Registry, and deploy the full working stack on the Raspberry Pi with a single command. Includes staging-to-production Let's Encrypt cert switch and cutover from the old systemd-based deployment.

</domain>

<decisions>
## Implementation Decisions

### Container registry
- Push to GitHub Container Registry (ghcr.io) — public images
- Two images under the same namespace:
  - `ghcr.io/ainxtgendev/stecher-tennis-app`
  - `ghcr.io/ainxtgendev/stecher-tennis-caddy`
- docker-compose.yml uses GHCR `image:` references (replaces current `build:` directives)
- A separate `docker-compose.build.yml` override file for local builds on NUC8

### Build strategy
- QEMU cross-compile on NUC8 via `docker buildx` — builds both linux/amd64 and linux/arm64 in one command
- Expect existing Dockerfiles to work as-is on ARM64 (python:3.12-slim and caddy:2-builder-alpine have ARM64 variants); verify during smoke test, fix only if needed
- A `build-and-push.sh` shell script that:
  - Creates the buildx builder (if not exists)
  - Builds both images for linux/amd64,linux/arm64
  - Pushes to GHCR
  - Reads `GHCR_TOKEN` from environment for authentication (document PAT creation with `write:packages` scope)

### RPi deployment procedure
- Git clone the repo on RPi; updates via `git pull && docker compose pull && docker compose up -d`
- `.env` file set up manually once on RPi from `.env.example`
- Full cutover script that SSHs to RPi (`stecher` alias → `192.168.1.213`):
  - Stops and disables old systemd service
  - Stops old Caddy
  - Runs `docker compose pull && docker compose up -d`
  - Verifies health endpoint
- Staging-to-production Let's Encrypt switch is part of Phase 4 deployment:
  - Update ACME_CA in .env to production URL
  - Clear caddy_data volume
  - Restart stack
  - Verify real Let's Encrypt certificate

### Image tagging
- Tag with app version from index.html (e.g., `v3.46`) AND `:latest`
- Build script reads version automatically
- docker-compose.yml uses `:latest` — updates are just `docker compose pull && up`
- Version tags exist in GHCR for manual rollback if needed
- Both app and caddy images share the same version tag — built and pushed together

### Claude's Discretion
- Buildx builder name and configuration
- Build script error handling and output formatting
- Exact cutover script structure and SSH commands
- How to extract app version from index.html in the build script
- QEMU setup commands (binfmt_misc registration)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Docker infrastructure (Phase 1-3 output)
- `Dockerfile` — Multi-stage build, python:3.12-slim, non-root appuser, HEALTHCHECK, DB_PATH
- `Dockerfile.caddy` — xcaddy build with caddy-dns/duckdns module
- `docker-compose.yml` — Two services (app + caddy), internal network, named volumes, env_file
- `Caddyfile` — HTTPS with DNS-01 ACME, HTTP redirect, env var substitution
- `.env.example` — All env vars including DUCKDNS_DOMAIN, DUCKDNS_TOKEN, ACME_CA, HTTPS_PORT
- `entrypoint.sh` — App entrypoint (init_db + gunicorn)

### Existing production setup (for cutover)
- `documentation/99_rpi.txt` — Current RPi systemd service name, Caddy setup, DuckDNS cron — needed to know what to stop/disable during cutover

### Prior phase context
- `.planning/phases/01-app-container/01-CONTEXT.md` — Dockerfile decisions, DB_PATH, non-root user
- `.planning/phases/02-compose-stack/02-CONTEXT.md` — Compose structure, volume strategy, env_file pattern
- `.planning/phases/03-https-via-caddy/03-CONTEXT.md` — HTTPS setup, ACME staging/production toggle, cert switchover procedure

### Requirements
- `.planning/REQUIREMENTS.md` — CONT-05 defines Phase 4 acceptance criteria

### Version source
- `templates/index.html` — Contains app version string (currently 3.46) used for image tagging

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Dockerfile`: Already multi-stage with build-essential/libffi-dev for C extensions — should cross-compile for ARM64 via QEMU without changes
- `Dockerfile.caddy`: Uses caddy:2-builder-alpine (has ARM64 variant) — should work as-is
- `docker-compose.yml`: Already has both services, volumes, env_file, restart policy, depends_on — just needs image: references swapped in
- `.env.example`: Complete with staging ACME_CA default and documented switchover procedure

### Established Patterns
- `restart: unless-stopped` already set on both services — handles RPi reboot auto-restart (success criterion #3)
- `env_file: .env` on both services — RPi just needs its own .env file
- HEALTHCHECK on app container — deployment script can verify after startup

### Integration Points
- `docker-compose.yml`: Replace `build:` with `image: ghcr.io/ainxtgendev/stecher-tennis-app:latest` and `image: ghcr.io/ainxtgendev/stecher-tennis-caddy:latest`
- New `docker-compose.build.yml`: Override file that restores `build:` directives for local development
- New `build-and-push.sh`: Build + push script for NUC8
- New `deploy.sh`: Full cutover script (SSH to RPi, stop old services, start Docker stack)
- `~/.bash_aliases`: `stecher` alias already configured for SSH to RPi at 192.168.1.213

</code_context>

<specifics>
## Specific Ideas

- RPi SSH alias is `stecher` (points to 192.168.1.213)
- DuckDNS domain is `nechvatal.duckdns.org` — production cert must be obtained on RPi (not NUC8)
- Phase 3 staging certs were validated on NUC8; Phase 4 must validate production certs on RPi
- Current app version is 3.46 (from templates/index.html)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-multi-arch-rpi-deploy*
*Context gathered: 2026-03-19*
