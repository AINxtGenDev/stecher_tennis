# Phase 4: Multi-Arch & RPi Deploy - Research

**Researched:** 2026-03-19
**Domain:** Docker multi-architecture builds, GHCR registry, Raspberry Pi deployment
**Confidence:** HIGH

## Summary

Phase 4 builds multi-architecture Docker images (AMD64 + ARM64) for both the app and custom Caddy containers, pushes them to GitHub Container Registry, and deploys the full stack on the Raspberry Pi. The existing Dockerfiles from Phases 1-3 form a solid foundation. Both base images (`python:3.12-slim` and `caddy:2-builder-alpine`/`caddy:2-alpine`) have verified ARM64 variants. Critical C-extension packages (bcrypt 4.3.0, greenlet 3.1.1) ship pre-built `manylinux_2017_aarch64` wheels, so pip install under QEMU emulation will download wheels rather than compile from source, making the ARM64 build practical.

The NUC8 build host has Docker 29.3.0 with buildx v0.31.1 installed, but currently lacks QEMU binfmt_misc registration for aarch64 and uses only the default builder (no docker-container driver). Setup of QEMU + a new buildx builder instance is required before the first multi-platform build. The RPi currently runs the app via systemd service (`stecher-tennis.service`) and bare-metal Caddy -- both must be stopped and disabled during cutover. SSH access is via `ssh stecher` (alias configured in `~/.ssh/config`, port 10115, key-based auth).

**Primary recommendation:** Create a `build-and-push.sh` script that handles QEMU setup, buildx builder creation, version extraction, and multi-platform build+push in one idempotent command. Create a separate `deploy.sh` for RPi cutover that SSHs to the Pi, stops old services, pulls images, and starts the Docker stack.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Push to GitHub Container Registry (ghcr.io) -- public images
- Two images: `ghcr.io/ainxtgendev/stecher-tennis-app` and `ghcr.io/ainxtgendev/stecher-tennis-caddy`
- docker-compose.yml uses GHCR `image:` references (replaces current `build:` directives)
- A separate `docker-compose.build.yml` override file for local builds on NUC8
- QEMU cross-compile on NUC8 via `docker buildx` -- builds both linux/amd64 and linux/arm64 in one command
- Expect existing Dockerfiles to work as-is on ARM64; verify during smoke test, fix only if needed
- A `build-and-push.sh` shell script (creates buildx builder, builds both images, pushes to GHCR, reads `GHCR_TOKEN` from environment)
- Git clone the repo on RPi; updates via `git pull && docker compose pull && docker compose up -d`
- `.env` file set up manually once on RPi from `.env.example`
- Full cutover script that SSHs to RPi (`stecher` alias -> `192.168.1.213`)
- Staging-to-production Let's Encrypt switch is part of Phase 4 deployment
- Tag with app version from index.html (e.g., `v3.46`) AND `:latest`
- Build script reads version automatically
- docker-compose.yml uses `:latest` -- updates are just `docker compose pull && up`
- Both app and caddy images share the same version tag -- built and pushed together

### Claude's Discretion
- Buildx builder name and configuration
- Build script error handling and output formatting
- Exact cutover script structure and SSH commands
- How to extract app version from index.html in the build script
- QEMU setup commands (binfmt_misc registration)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CONT-05 | Docker image builds for both ARM64 and AMD64 via `docker buildx` | Verified: python:3.12-slim has linux/arm64, caddy:2-builder-alpine has linux/arm64/v8, bcrypt/greenlet have aarch64 wheels. NUC8 has buildx v0.31.1 but needs QEMU setup and docker-container builder creation. |
</phase_requirements>

## Standard Stack

### Core (already installed on NUC8)
| Tool | Version | Purpose | Verified |
|------|---------|---------|----------|
| Docker Engine | 29.3.0 | Container runtime | `docker --version` on NUC8 |
| Docker Buildx | 0.31.1 | Multi-platform build plugin | `docker buildx version` on NUC8 |
| tonistiigi/binfmt | latest | QEMU binary registration for ARM64 emulation | Needs initial setup |

### Base Images (ARM64 support verified via manifest inspect)
| Image | ARM64 Platform | Verified |
|-------|---------------|----------|
| python:3.12-slim | linux/arm64 | `docker buildx imagetools inspect` -- confirmed |
| caddy:2-builder-alpine | linux/arm64/v8 | `docker buildx imagetools inspect` -- confirmed |
| caddy:2-alpine | linux/arm64/v8 | `docker buildx imagetools inspect` -- confirmed |

### Python Packages with C Extensions (ARM64 wheel availability)
| Package | Version | aarch64 Wheel | Verified |
|---------|---------|---------------|----------|
| bcrypt | 4.3.0 | `bcrypt-4.3.0-cp39-abi3-manylinux_2_17_aarch64.whl` | `pip download --platform` confirmed |
| greenlet | 3.1.1 | `greenlet-3.1.1-cp312-cp312-manylinux_2_17_aarch64.whl` | PyPI files page confirmed |

### RPi Deployment Target
| Property | Value | Source |
|----------|-------|--------|
| SSH alias | `stecher` (in `~/.ssh/config`) | Verified in SSH config |
| SSH host | 192.168.1.213 | SSH config |
| SSH port | 10115 | SSH config |
| SSH key | `~/.ssh/stecher_tennis_key` | SSH config |
| SSH user | stecher | SSH config |
| Old systemd service | `stecher-tennis.service` | `documentation/99_rpi.txt` |
| Old Caddy | `caddy.service` (apt-installed) | `documentation/99_rpi.txt` |
| DuckDNS domain | `nechvatal.duckdns.org` | `.env.example` and docs |
| Current app version | 3.46 | `templates/index.html` |

## Architecture Patterns

### Build-and-Push Script Flow
```
build-and-push.sh
  1. Validate GHCR_TOKEN is set
  2. Extract version from templates/index.html
  3. Ensure QEMU binfmt is registered (idempotent)
  4. Create/use buildx builder with docker-container driver (idempotent)
  5. Login to ghcr.io
  6. Build + push app image (both platforms, tagged :latest and :vX.XX)
  7. Build + push caddy image (both platforms, tagged :latest and :vX.XX)
  8. Print summary
```

### docker-compose.yml Modification
```yaml
# BEFORE (Phase 1-3):
services:
  app:
    build: .
    image: tennis-app:latest
  caddy:
    build:
      context: .
      dockerfile: Dockerfile.caddy

# AFTER (Phase 4):
services:
  app:
    image: ghcr.io/ainxtgendev/stecher-tennis-app:latest
  caddy:
    image: ghcr.io/ainxtgendev/stecher-tennis-caddy:latest
```

### docker-compose.build.yml Override (for local development on NUC8)
```yaml
# Usage: docker compose -f docker-compose.yml -f docker-compose.build.yml up -d --build
services:
  app:
    build: .
  caddy:
    build:
      context: .
      dockerfile: Dockerfile.caddy
```

### RPi Cutover Script Flow
```
deploy.sh
  1. SSH to RPi (via stecher alias/config)
  2. Stop and disable stecher-tennis.service
  3. Stop and disable caddy.service
  4. Ensure Docker is installed and enabled
  5. Clone repo (if first deploy) or git pull
  6. Create .env from .env.example (manual step -- script prompts)
  7. docker compose pull
  8. docker compose up -d
  9. Wait for health check
  10. Switch ACME_CA to production (update .env)
  11. Clear caddy_data volume
  12. Restart stack
  13. Verify production certificate
```

### Version Extraction Pattern
```bash
# Extracts "3.46" from the index.html version string
VERSION=$(grep -oP 'Version:\s*\K[0-9]+\.[0-9]+' templates/index.html)
```

### Recommended Project Structure (new files only)
```
project-root/
  build-and-push.sh         # NEW: multi-arch build + GHCR push
  deploy.sh                 # NEW: RPi cutover script
  docker-compose.yml        # MODIFIED: image: refs replace build:
  docker-compose.build.yml  # NEW: local build override
  Dockerfile                # UNCHANGED
  Dockerfile.caddy          # UNCHANGED (or minimal TARGETARCH tweak)
  Caddyfile                 # UNCHANGED
  .env.example              # UNCHANGED
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| QEMU registration | Manual binfmt_misc setup | `docker run --privileged --rm tonistiigi/binfmt --install all` | Handles kernel registration, binary paths, fix_binary flags correctly |
| Multi-platform builder | Manual buildx config | `docker buildx create --name multiarch --driver docker-container --bootstrap --use` | docker-container driver is required for multi-platform push |
| ARM64 package compilation | Cross-compiling C extensions | Pre-built wheels from PyPI (bcrypt, greenlet both have aarch64 wheels) | QEMU emulation + pip downloading wheels is the standard approach |
| Registry login | curl-based API auth | `echo $GHCR_TOKEN \| docker login ghcr.io -u USERNAME --password-stdin` | Standard Docker auth, stores credentials in config.json |

## Common Pitfalls

### Pitfall 1: Default Builder Cannot Do Multi-Platform Push
**What goes wrong:** `docker buildx build --platform linux/amd64,linux/arm64 --push` fails with the default `docker` driver.
**Why it happens:** The default builder uses the `docker` driver which only supports single-platform builds and cannot push multi-platform manifests.
**How to avoid:** Always create a builder with `--driver docker-container`. The build script should create one if not exists.
**Warning signs:** Error message mentioning "docker driver does not support multi-platform output."

### Pitfall 2: QEMU Not Registered
**What goes wrong:** ARM64 build stage fails immediately with "exec format error" or similar.
**Why it happens:** binfmt_misc entries for aarch64 are not registered. The NUC8 currently has NO aarch64 binfmt entry.
**How to avoid:** Run `docker run --privileged --rm tonistiigi/binfmt --install all` before the first build. This is idempotent -- safe to re-run.
**Warning signs:** `ls /proc/sys/fs/binfmt_misc/` shows no `qemu-aarch64` entry.

### Pitfall 3: --load Does Not Work for Multi-Platform
**What goes wrong:** Trying to `--load` a multi-platform image into local Docker fails.
**Why it happens:** Docker's local image store only supports one platform at a time. Multi-platform images must be pushed to a registry.
**How to avoid:** Always use `--push` with multi-platform builds. To test locally, build single-platform with `--load`.
**Warning signs:** Error: "docker exporter does not currently support exporting manifest lists."

### Pitfall 4: Docker Service Not Enabled on RPi
**What goes wrong:** After RPi reboot, containers don't restart despite `restart: unless-stopped` policy.
**Why it happens:** The Docker daemon itself is not enabled to start on boot. `restart: unless-stopped` only works if Docker is running.
**How to avoid:** Run `sudo systemctl enable docker` on the RPi during initial setup.
**Warning signs:** `sudo systemctl is-enabled docker` returns "disabled."

### Pitfall 5: Old Services Conflict on RPi
**What goes wrong:** Port conflicts or duplicate processes after deploying Docker stack.
**Why it happens:** The old systemd `stecher-tennis.service` and `caddy.service` are still running/enabled.
**How to avoid:** The cutover script must `systemctl stop && systemctl disable` both old services before starting Docker.
**Warning signs:** "Address already in use" errors in `docker compose logs`.

### Pitfall 6: GHCR Token Missing write:packages Scope
**What goes wrong:** `docker push` to ghcr.io returns 403 Forbidden or authentication errors.
**Why it happens:** The GitHub Personal Access Token (PAT) lacks the `write:packages` scope.
**How to avoid:** Document PAT creation requirements. Build script should validate GHCR_TOKEN is set before attempting build.
**Warning signs:** Push fails with "denied: permission_denied" after successful build.

### Pitfall 7: Staging ACME_CA Still Set on RPi
**What goes wrong:** HTTPS works but browser shows untrusted certificate warning.
**Why it happens:** `.env` on RPi still has the staging ACME CA URL instead of production.
**How to avoid:** The deploy script must update ACME_CA to production URL, clear caddy_data volume, and restart.
**Warning signs:** Certificate issuer shows "STAGING" in the browser certificate details.

### Pitfall 8: Caddy Data Volume Not Cleared After ACME Switch
**What goes wrong:** Caddy keeps using the old staging certificate even after changing ACME_CA.
**Why it happens:** Caddy caches certificates in the `caddy_data` volume. It will not re-issue if a cert already exists.
**How to avoid:** After changing ACME_CA, run `docker compose down`, remove the caddy_data volume, then `docker compose up -d`.
**Warning signs:** Certificate still shows staging issuer despite production ACME_CA in .env.

## Code Examples

### QEMU Setup + Builder Creation (idempotent)
```bash
# Register QEMU binary handlers (survives until reboot)
docker run --privileged --rm tonistiigi/binfmt --install all

# Create a multi-platform builder (idempotent -- errors if exists, which is fine)
docker buildx create --name multiarch --driver docker-container --bootstrap --use 2>/dev/null || \
    docker buildx use multiarch
```
Source: Docker official docs (https://docs.docker.com/build/building/multi-platform/)

### GHCR Authentication
```bash
# Login to GitHub Container Registry
echo "${GHCR_TOKEN}" | docker login ghcr.io -u "${GHCR_USER:-ainxtgendev}" --password-stdin
```
Source: GitHub docs, verified via multiple community examples

### Multi-Platform Build + Push
```bash
# Build and push app image for both platforms
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    --tag ghcr.io/ainxtgendev/stecher-tennis-app:latest \
    --tag ghcr.io/ainxtgendev/stecher-tennis-app:v${VERSION} \
    --push \
    .

# Build and push caddy image for both platforms
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    --tag ghcr.io/ainxtgendev/stecher-tennis-caddy:latest \
    --tag ghcr.io/ainxtgendev/stecher-tennis-caddy:v${VERSION} \
    --push \
    -f Dockerfile.caddy \
    .
```
Source: Docker buildx docs

### Version Extraction
```bash
VERSION=$(grep -oP 'Version:\s*\K[0-9]+\.[0-9]+' templates/index.html)
if [ -z "$VERSION" ]; then
    echo "ERROR: Could not extract version from templates/index.html"
    exit 1
fi
echo "Building version: v${VERSION}"
```
Verified: Pattern matches `Version: 3.46` in current index.html

### RPi Service Cutover (SSH commands)
```bash
# Stop and disable old services
ssh stecher "sudo systemctl stop stecher-tennis.service && sudo systemctl disable stecher-tennis.service"
ssh stecher "sudo systemctl stop caddy.service && sudo systemctl disable caddy.service"

# Ensure Docker starts on boot
ssh stecher "sudo systemctl enable docker"
```
Source: `documentation/99_rpi.txt` -- service names verified

### ACME Staging-to-Production Switch
```bash
# On RPi: update .env
ssh stecher "cd ~/stecher_tennis && sed -i 's|acme-staging-v02|acme-v02|' .env"

# Remove cached staging certs
ssh stecher "cd ~/stecher_tennis && docker compose down"
ssh stecher "cd ~/stecher_tennis && docker volume rm \$(docker volume ls -q | grep caddy_data)"
ssh stecher "cd ~/stecher_tennis && docker compose up -d"
```
Source: `.env.example` switchover procedure

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate `docker-compose` binary (v1) | `docker compose` CLI plugin (v2) | Docker Compose v2 (2021) | Use `docker compose` not `docker-compose` |
| Build images per-architecture separately | `docker buildx` multi-platform manifests | BuildKit default since Docker 23.0 | Single command builds for all archs |
| `docker-compose.yml` `version:` key | Omitted (deprecated) | Compose v2 | Already handled in Phase 2 |
| Manual binfmt_misc setup | `tonistiigi/binfmt` container | ~2020 | One-liner QEMU setup |

## Open Questions

1. **Docker installed on RPi?**
   - What we know: RPi runs Raspberry Pi OS, has systemd, has the old bare-metal deployment
   - What's unclear: Whether Docker is already installed on the RPi or needs fresh installation
   - Recommendation: Deploy script should check `docker --version` and install via convenience script if missing. Include `curl -fsSL https://get.docker.com | sh` as a documented prerequisite.

2. **RPi OS 32-bit vs 64-bit?**
   - What we know: We are building `linux/arm64` images. The RPi 4 hardware supports 64-bit.
   - What's unclear: Whether the RPi currently runs 32-bit or 64-bit Raspberry Pi OS.
   - Recommendation: The deploy script should verify architecture with `uname -m` (must show `aarch64`). If 32-bit, ARM64 images won't run and the user would need to reinstall the OS. Add this as a pre-flight check.

3. **QEMU build time for the Caddy image**
   - What we know: xcaddy compiles Go code. Under QEMU emulation, Go compilation for ARM64 will be significantly slower than native (4-5x estimated).
   - What's unclear: Exact build time. Could be 5-15 minutes for the Caddy image.
   - Recommendation: Acceptable for a one-off manual build. Document expected build time. Could optimize with TARGETARCH cross-compilation in Dockerfile.caddy, but not required.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | None (defaults work) |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CONT-05a | Multi-arch build completes for linux/amd64,linux/arm64 | smoke/manual | `docker buildx build --platform linux/amd64,linux/arm64 --push .` | N/A -- build script IS the test |
| CONT-05b | App runs on RPi after pulling GHCR image | smoke/manual | `ssh stecher "cd ~/stecher_tennis && docker compose ps"` + health check | N/A -- deploy script verifies |
| CONT-05c | HTTPS works with production cert on RPi | smoke/manual | `curl -s https://nechvatal.duckdns.org:10443/health` | N/A -- deploy script verifies |
| CONT-05d | Data persists across container restart | smoke/manual | Restart containers, verify data | N/A -- manual verification |
| CONT-05e | WebSocket connects through Caddy on RPi | smoke/manual | Browser test or curl upgrade header | N/A -- manual verification |
| CONT-05f | Containers restart after RPi reboot | smoke/manual | `ssh stecher "sudo reboot"` + wait + verify | N/A -- manual verification |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q` (existing unit tests still pass)
- **Per wave merge:** Build script dry-run + full pytest
- **Phase gate:** Full deploy to RPi + all smoke tests pass

### Wave 0 Gaps
None -- this phase is primarily shell scripts and Docker config changes. Existing pytest tests cover app functionality. Phase 4 validation is inherently manual/smoke-test based (SSH to RPi, verify services, check certificates). No new automated test files needed.

## Sources

### Primary (HIGH confidence)
- Docker official docs: Multi-platform builds -- https://docs.docker.com/build/building/multi-platform/
- `docker buildx imagetools inspect python:3.12-slim` -- ARM64 platform confirmed
- `docker buildx imagetools inspect caddy:2-builder-alpine` -- ARM64/v8 platform confirmed
- `docker buildx imagetools inspect caddy:2-alpine` -- ARM64/v8 platform confirmed
- `pip download --platform manylinux2014_aarch64 bcrypt==4.3.0` -- aarch64 wheel confirmed
- PyPI greenlet 3.1.1 files page -- aarch64 wheel confirmed
- `docker buildx version` on NUC8 -- v0.31.1 confirmed
- `~/.ssh/config` on NUC8 -- SSH alias `stecher`, port 10115, key path confirmed
- `documentation/99_rpi.txt` -- old service names, Caddy setup, DuckDNS cron confirmed

### Secondary (MEDIUM confidence)
- Docker restart policies: https://docs.docker.com/engine/containers/start-containers-automatically/
- GHCR authentication pattern: verified across multiple community sources
- RPi Docker installation via convenience script: https://get.docker.com

### Tertiary (LOW confidence)
- QEMU build performance (4-5x slowdown estimate): community reports, not benchmarked on this specific hardware
- RPi OS bitness assumption (64-bit): assumed based on building ARM64 images, needs verification on actual RPi

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all tools verified locally on NUC8, base image architectures confirmed via manifest inspect
- Architecture patterns: HIGH -- standard docker buildx workflow, well-documented
- Pitfalls: HIGH -- verified against current NUC8 state (no QEMU, no builder, no GHCR auth)
- RPi deployment: MEDIUM -- SSH config verified, old service names from docs, but RPi Docker state unknown

**Research date:** 2026-03-19
**Valid until:** 2026-04-19 (stable tooling, unlikely to change)
