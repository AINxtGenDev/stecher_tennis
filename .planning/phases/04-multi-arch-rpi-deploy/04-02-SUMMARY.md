---
phase: 04-multi-arch-rpi-deploy
plan: 02
subsystem: infra
tags: [deploy, rpi, ssh, systemd, letsencrypt, acme, cutover, arm64]

# Dependency graph
requires:
  - phase: 04-multi-arch-rpi-deploy
    provides: build-and-push.sh multi-arch build script, GHCR image references in docker-compose.yml
  - phase: 03-https-via-caddy
    provides: Caddyfile with DuckDNS ACME, Dockerfile.caddy with xcaddy
provides:
  - deploy.sh RPi cutover automation script (systemd to Docker)
  - Verified production deployment on Raspberry Pi with HTTPS
  - Reboot-resilient Docker stack on ARM64 hardware
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: [ssh-remote-command-wrapper, interactive-acme-switchover, health-check-via-docker-exec]

key-files:
  created:
    - deploy.sh
  modified:
    - Caddyfile
    - docker-compose.yml

key-decisions:
  - "Port 443 internal: FritzBox maps external 10443 to internal 443, so Caddy must listen on 443 (not 10443)"
  - "Health check via docker compose exec: curl not installed in slim container, use exec to hit localhost:5000 inside container"
  - "Clone docker branch explicitly: deploy.sh clones the docker branch, not main, since Docker files live on docker branch"
  - "Repo URL casing: GitHub URL is case-sensitive, fixed to match actual repo name"

patterns-established:
  - "RPi deployment pattern: deploy.sh runs from NUC8, executes all steps via SSH to RPi"
  - "ACME staging-first: deploy with staging certs, verify, then interactively switch to production"
  - "Non-git directory handling: backup existing dir before fresh clone to avoid data loss"

requirements-completed: [CONT-05]

# Metrics
duration: 82min
completed: 2026-03-19
---

# Phase 04 Plan 02: RPi Deployment Summary

**deploy.sh automates full RPi cutover from systemd to Docker stack -- stops old services, pulls GHCR multi-arch images, starts containers with staging certs, then switches to production Let's Encrypt via interactive prompt; verified end-to-end with HTTPS, WebSocket, and reboot resilience**

## Performance

- **Duration:** ~82 min (includes human-verify checkpoint for live RPi deployment)
- **Started:** 2026-03-19T10:59:00Z
- **Completed:** 2026-03-19T12:21:00Z
- **Tasks:** 2
- **Files modified:** 3 (deploy.sh created, Caddyfile and docker-compose.yml modified)

## Accomplishments
- Created deploy.sh that automates the complete RPi cutover: pre-flight checks, old service shutdown, Docker enablement, repo clone, image pull, stack startup, health check, and ACME cert switchover
- Successfully deployed to production Raspberry Pi with working HTTPS via Let's Encrypt production certificate
- Verified WebSocket/Socket.IO connectivity through HTTPS on the RPi
- Confirmed containers auto-restart after RPi reboot (both services healthy post-reboot)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create deploy.sh RPi cutover script** - `6043602` (feat)
   - Fix: `6f3962e` - Port 443 internally for FritzBox forwarding
   - Fix: `6892e19` - deploy.sh fixes from live RPi deployment
2. **Task 2: Verify RPi deployment end-to-end** - checkpoint:human-verify (approved, no code commit)

## Files Created/Modified
- `deploy.sh` - RPi cutover automation: SSH pre-flight, systemd service stop/disable, Docker enable, repo clone (docker branch), GHCR image pull, stack startup, health check loop, interactive ACME staging-to-production switch
- `Caddyfile` - Changed HTTPS listen port to 443 (matching FritzBox internal forwarding)
- `docker-compose.yml` - Changed published port from 10443:10443 to 443:443 (matching FritzBox forwarding)

## Decisions Made
- **Port 443 internal mapping**: FritzBox forwards external port 10443 to internal port 443 on the RPi. Caddy and docker-compose.yml updated to listen on 443 internally rather than 10443. External users still access via port 10443.
- **Health check via docker compose exec**: The slim Python container does not include curl. Changed health check from `curl localhost:5000` to `docker compose exec app curl` (or equivalent exec-based check) to verify app health.
- **Clone docker branch**: deploy.sh explicitly clones the `docker` branch since Docker infrastructure files are not yet merged to main.
- **Backup existing non-git dirs**: If `~/stecher_tennis` exists but is not a git repo, deploy.sh backs it up to `stecher_tennis.bak.<timestamp>` before cloning fresh.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Caddyfile/docker-compose.yml port mismatch with FritzBox**
- **Found during:** Task 2 (live RPi deployment verification)
- **Issue:** FritzBox forwards external port 10443 to internal port 443 on the RPi, but Caddy was configured to listen on 10443 internally. TLS handshake failed because no service was listening on port 443.
- **Fix:** Changed Caddyfile HTTPS listen port to 443 and docker-compose.yml port mapping to 443:443
- **Files modified:** Caddyfile, docker-compose.yml
- **Verification:** Production HTTPS working at https://nechvatal.duckdns.org:10443
- **Committed in:** `6f3962e`

**2. [Rule 3 - Blocking] deploy.sh repo URL casing and clone logic**
- **Found during:** Task 2 (live RPi deployment)
- **Issue:** Repo URL had wrong casing (GitHub is case-sensitive), existing non-git directory blocked clone, and health check used curl which is not available in slim container
- **Fix:** Fixed repo URL to correct casing, added backup-and-reclone logic for non-git dirs, cloned docker branch explicitly, switched health check to docker compose exec
- **Files modified:** deploy.sh
- **Verification:** deploy.sh ran successfully on RPi, stack came up healthy
- **Committed in:** `6892e19`

**3. [Rule 3 - Blocking] RPi .env credentials**
- **Found during:** Task 2 (live RPi deployment)
- **Issue:** .env file on RPi needed real values for DUCKDNS_TOKEN, ACME_EMAIL, and SECRET_KEY
- **Fix:** Manual credential setup on RPi (human action, not automatable)
- **Files modified:** None (RPi-local .env only)
- **Verification:** Stack started successfully with real credentials

---

**Total deviations:** 3 auto-fixed (3 blocking issues)
**Impact on plan:** All fixes were necessary for the deployment to work on actual RPi hardware. No scope creep -- all changes directly support the deployment goal.

## Issues Encountered
- FritzBox port forwarding scheme (external 10443 to internal 443) was not documented in the plan context. Discovered during live deployment and fixed immediately.
- GitHub URL case sensitivity caused git clone failure on RPi. Fixed by correcting the URL in deploy.sh.
- Container health check approach needed to change because curl is not installed in the python:3.12-slim based app container.

## User Setup Required
None - deployment is complete and verified on RPi. Future redeployments use: `ssh stecher 'cd ~/stecher_tennis && docker compose pull && docker compose up -d'`

## Next Phase Readiness
- This is the final phase (Phase 4 of 4). All v1 requirements are complete.
- The Docker deployment milestone is fully delivered:
  - Multi-arch images (AMD64 + ARM64) build and push to GHCR
  - Production HTTPS with Let's Encrypt on RPi
  - WebSocket/Socket.IO working through HTTPS reverse proxy
  - Containers survive RPi reboot
  - One-command deployment via `docker compose pull && docker compose up -d`

## Self-Check: PASSED

- deploy.sh: FOUND
- Caddyfile: FOUND
- docker-compose.yml: FOUND
- Commit 6043602: FOUND
- Commit 6f3962e: FOUND
- Commit 6892e19: FOUND
- 04-02-SUMMARY.md: FOUND

---
*Phase: 04-multi-arch-rpi-deploy*
*Completed: 2026-03-19*
