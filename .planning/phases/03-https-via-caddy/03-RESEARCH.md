# Phase 3: HTTPS via Caddy - Research

**Researched:** 2026-03-19
**Domain:** Caddy reverse proxy with DNS-01 ACME (DuckDNS), Docker multi-stage xcaddy build
**Confidence:** HIGH

## Summary

Phase 3 replaces the Phase 2 plain-HTTP Caddy service with a custom-built Caddy image that includes the `caddy-dns/duckdns` module for DNS-01 ACME certificate provisioning. The current `caddy:2-alpine` image in `docker-compose.yml` becomes a multi-stage build using `caddy:2-builder-alpine` + xcaddy, producing a custom binary with the DuckDNS DNS provider compiled in. The Caddyfile is rewritten from a `:80` site block to a domain-based HTTPS site block with `tls { dns duckdns ... }`, plus an explicit HTTP-to-HTTPS redirect block.

A critical design detail: Caddy's automatic HTTP-to-HTTPS redirect does NOT include non-standard port numbers in the redirect URL. Since HTTPS is on port 10443 (not 443), the redirect from port 80 must be written manually as a separate `:80` site block with an explicit `redir` directive. Additionally, the `acme_ca` global option cannot accept an empty value -- using `{$ACME_CA}` when the env var is empty causes a parsing error ("Wrong argument count or unexpected line ending"). The CONTEXT.md decision of "remove or empty the `ACME_CA` line for production" requires careful Caddyfile design.

**Primary recommendation:** Use a two-block Caddyfile structure (HTTP redirect + HTTPS main site), with `acme_ca` placed inside a global options block only when set, leveraging the `{$ACME_CA}` env var substitution at parse-time. Since empty `acme_ca` causes parse errors, the cleanest approach is to conditionally include the entire global options line via env var expansion -- set `ACME_CA` to the full staging URL when testing, and leave it unset (Caddy defaults to Let's Encrypt + ZeroSSL production) when in production. The Caddyfile should NOT contain a literal `acme_ca` directive with a variable that might be empty.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Domain configured via `DUCKDNS_DOMAIN` env var in `.env` (value: `nechvatal`)
- Caddyfile uses `{$DUCKDNS_DOMAIN}.duckdns.org` -- not hardcoded
- DuckDNS token passed via `DUCKDNS_TOKEN` env var in `.env`
- TLS email configurable via `ACME_EMAIL` env var (value: `otto.kuegerl@gmail.com`)
- DuckDNS IP updates handled externally by existing RPi cron -- Docker does NOT update DuckDNS IP
- Token is only used for DNS-01 ACME challenge inside the Caddy container
- All env vars passed to Caddy service via single shared `.env` file (no separate caddy.env)
- Caddy listens on port 10443 (HTTPS) and port 80 (HTTP redirect) inside Docker
- Docker maps `10443:10443` and `80:80` to host
- No FritzBox port translation needed -- Caddy serves directly on the external-facing port
- HTTPS port configurable via `HTTPS_PORT` env var in `.env` (default: 10443)
- HTTP requests to port 80 redirect permanently to `https://{$DUCKDNS_DOMAIN}.duckdns.org:{$HTTPS_PORT}{uri}`
- CORS_ALLOWED_ORIGINS in `.env.example` updated to `https://nechvatal.duckdns.org:10443`
- ACME endpoint toggled via `ACME_CA` env var in `.env`
- `.env.example` ships with staging URL as default: `https://acme-staging-v02.api.letsencrypt.org/directory`
- For production: remove or empty the `ACME_CA` line (Caddy defaults to Let's Encrypt production)
- When switching staging to production: clear `caddy_data` volume (`docker volume rm`) for clean slate
- Documented switchover procedure: edit .env, docker compose down, docker volume rm caddy_data, docker compose up -d
- Phase 3 smoke tests run on NUC8 with staging certs; production cert verification deferred to Phase 4 on RPi

### Claude's Discretion
- xcaddy Dockerfile structure and base image choice
- Caddy global options block (if needed)
- Exact Caddyfile formatting and log configuration
- How to handle empty/unset ACME_CA in Caddyfile (conditional or default behavior)
- caddy_config volume addition (if needed alongside caddy_data)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| HTTP-01 | Custom Caddy image built with xcaddy + caddy-dns/duckdns module | Dockerfile.caddy multi-stage build pattern verified: `caddy:2-builder-alpine` -> xcaddy build -> `caddy:2-alpine` runtime. Module: `github.com/caddy-dns/duckdns` |
| HTTP-02 | Caddy serves HTTPS with automatic certificate via DuckDNS DNS-01 ACME challenge | Caddyfile `tls { dns duckdns {$DUCKDNS_TOKEN} }` syntax verified. Global `acme_ca` for staging toggle. `caddy_data:/data` volume persists certs |
| HTTP-03 | WebSocket connections pass through Caddy to Flask-SocketIO | Caddy v2 handles WebSocket upgrade automatically -- no special directives needed. Existing `header_up` directives from Phase 2 are sufficient |
| HTTP-04 | Toggle between Let's Encrypt staging and production ACME endpoints via env var | `ACME_CA` env var in global options block. Critical pitfall: empty value causes parse error. Design pattern documented below |
</phase_requirements>

## Standard Stack

### Core
| Library/Tool | Version | Purpose | Why Standard |
|-------------|---------|---------|--------------|
| caddy | 2.11.2 | HTTPS reverse proxy with automatic cert management | Official Docker image, built-in ACME, auto-renew, HTTP/2 |
| xcaddy | (in builder image) | Build Caddy with custom modules | Official tool for compiling Caddy with plugins |
| caddy-dns/duckdns | latest (via xcaddy) | DNS-01 ACME challenge provider for DuckDNS | Only way to get Let's Encrypt certs for DuckDNS domains without port 443 access |

### Supporting
| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| caddy:2-builder-alpine | 2.11.2 | Multi-stage build base with xcaddy pre-installed | Dockerfile.caddy builder stage |
| caddy:2-alpine | 2.11.2 | Lightweight runtime image (~40MB) | Dockerfile.caddy runtime stage |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom xcaddy build | serfriz/caddy-duckdns pre-built image | Simpler but third-party dependency; custom build gives full control |
| caddy:2-alpine runtime | caddy:2 (Debian) | Alpine is smaller (~40MB vs ~80MB); sufficient for Caddy's Go binary |

**No installation needed** -- all dependencies are Docker images pulled during build.

## Architecture Patterns

### Recommended Project Structure
```
project-root/
  Dockerfile           # App container (existing, unchanged)
  Dockerfile.caddy     # NEW: Custom Caddy with duckdns module
  Caddyfile            # MODIFIED: HTTPS + DNS-01 + HTTP redirect
  docker-compose.yml   # MODIFIED: caddy service uses build context
  .env.example         # MODIFIED: add Phase 3 env vars
  .env                 # User's actual config (gitignored)
```

### Pattern 1: Multi-Stage xcaddy Docker Build
**What:** Two-stage Dockerfile -- builder compiles Caddy with duckdns plugin, runtime copies just the binary.
**When to use:** Always, for any Caddy build with custom modules.
**Example:**
```dockerfile
# Source: https://hub.docker.com/_/caddy (official builder docs)
# Source: https://caddyserver.com/docs/build
FROM caddy:2-builder-alpine AS builder

RUN xcaddy build \
    --with github.com/caddy-dns/duckdns

FROM caddy:2-alpine

COPY --from=builder /usr/bin/caddy /usr/bin/caddy
```
**Confidence:** HIGH -- verified against official Docker Hub docs and Caddy build docs.

### Pattern 2: Caddyfile with DNS-01 ACME and HTTP Redirect
**What:** Two site blocks -- one for HTTPS with DNS-01 challenge, one for HTTP-to-HTTPS redirect with non-standard port.
**When to use:** When HTTPS runs on a non-standard port (10443 in this case).
**Critical detail:** Caddy's auto-redirect does NOT include non-standard ports in the redirect URL. A manual `:80` block is required.
**Example:**
```
# Source: https://caddyserver.com/docs/caddyfile/options
# Source: https://github.com/caddy-dns/duckdns (README)
# Source: https://caddy.community/t/how-to-make-auto-https-redirect-to-my-custom-https-port/8051
{
    acme_ca {$ACME_CA}
    email   {$ACME_EMAIL}
}

{$DUCKDNS_DOMAIN}.duckdns.org:{$HTTPS_PORT} {
    tls {
        dns duckdns {$DUCKDNS_TOKEN}
    }

    log {
        output stderr
        level ERROR
    }

    reverse_proxy app:5000 {
        header_up Host              {http.request.host}
        header_up X-Real-IP         {http.request.remote}
        header_up X-Forwarded-For   {http.request.remote}
        header_up X-Forwarded-Proto {http.request.scheme}
    }
}

:80 {
    redir https://{$DUCKDNS_DOMAIN}.duckdns.org:{$HTTPS_PORT}{uri} permanent
}
```
**Confidence:** HIGH for the overall pattern; MEDIUM for the `{$ACME_CA}` handling (see Pitfall 1 below).

### Pattern 3: Docker Compose Build Context for Caddy
**What:** Replace `image: caddy:2-alpine` with `build:` pointing to `Dockerfile.caddy`.
**When to use:** When the caddy service needs a custom-built image.
**Example:**
```yaml
caddy:
    build:
      context: .
      dockerfile: Dockerfile.caddy
    networks:
      - tennis_net
    ports:
      - "${HTTPS_PORT:-10443}:${HTTPS_PORT:-10443}"
      - "80:80"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
    env_file: .env
    restart: unless-stopped
    depends_on:
      app:
        condition: service_healthy
```
**Confidence:** HIGH -- standard Docker Compose pattern.

### Anti-Patterns to Avoid
- **Hardcoding the DuckDNS domain in Caddyfile:** Use `{$DUCKDNS_DOMAIN}.duckdns.org` for portability.
- **Using `caddy:2-alpine` image directly with DuckDNS:** The standard image does not include the duckdns DNS provider module. You will get `module not registered: dns.providers.duckdns`.
- **Using `{env.DUCKDNS_TOKEN}` (runtime) for the token in the tls block:** Use `{$DUCKDNS_TOKEN}` (parse-time) instead. The `{env.*}` form requires module support and may not work in all contexts. The `{$...}` form is substituted before parsing, guaranteed to work everywhere.
- **Relying on Caddy auto-redirect with non-standard HTTPS port:** Auto-redirect produces `Location: https://domain/path` WITHOUT the `:10443` port. You MUST write a manual `:80` redirect block.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TLS certificate management | Manual certbot, cron renewal | Caddy automatic HTTPS | Caddy handles issuance, renewal, OCSP stapling automatically |
| DNS-01 ACME challenge | Custom DNS update scripts | caddy-dns/duckdns module | Handles TXT record creation/cleanup, propagation waiting |
| HTTP-to-HTTPS redirect | Custom Flask redirect middleware | Caddy `:80 { redir ... }` block | Handled at reverse proxy layer before reaching app |
| WebSocket upgrade proxying | Manual Connection/Upgrade header handling | Caddy v2 reverse_proxy (built-in) | Caddy v2 automatically handles WebSocket upgrade -- no special config needed |

**Key insight:** Caddy handles the entire TLS lifecycle (certificate acquisition, storage, renewal, OCSP stapling) and WebSocket proxying automatically. The only custom work needed is building the binary with the DuckDNS module and writing the correct Caddyfile.

## Common Pitfalls

### Pitfall 1: Empty ACME_CA Env Var Causes Parse Error
**What goes wrong:** If `ACME_CA` env var is empty or unset, `acme_ca {$ACME_CA}` expands to `acme_ca ` (no argument), causing "Wrong argument count or unexpected line ending after 'acme_ca'" error.
**Why it happens:** `{$...}` env vars are substituted BEFORE Caddyfile parsing. An empty var leaves the directive with no argument.
**How to avoid:** Two approaches (Claude's discretion per CONTEXT.md):
  - **Option A (recommended):** Use the entire global options block as an env var. Set `CADDY_GLOBAL_OPTIONS` to `acme_ca https://acme-staging-v02.api.letsencrypt.org/directory` for staging, or leave empty for production. In Caddyfile: `{ {$CADDY_GLOBAL_OPTIONS} email {$ACME_EMAIL} }`. When empty, the global block just has `email`.
  - **Option B:** Keep `ACME_CA` as is but require it always be set. For production, set it to `https://acme-v02.api.letsencrypt.org/directory` (the Let's Encrypt production URL) rather than leaving it empty. This slightly diverges from "remove or empty" but avoids the parse error.
  - **Option C:** Avoid putting `acme_ca` in the global block entirely. Instead, set it per-site using the `tls` directive `ca` subdirective: `tls { dns duckdns {$DUCKDNS_TOKEN} \n ca {$ACME_CA} }`. Same empty-var problem applies though.
**Recommendation:** Option B is simplest and safest. Always require `ACME_CA` to be set. `.env.example` ships with staging URL. For production, change to the production URL rather than removing. This satisfies the CONTEXT.md intent (toggle via env var) without parse errors.
**Warning signs:** Caddy container exits immediately with parse error in logs.

### Pitfall 2: Caddy Auto-Redirect Omits Non-Standard Port
**What goes wrong:** With `https_port 10443`, Caddy's automatic HTTP redirect sends browsers to `https://domain/path` (port 443 assumed), not `https://domain:10443/path`.
**Why it happens:** Caddy's auto-redirect logic does not include the `https_port` value in the redirect URL.
**How to avoid:** Write an explicit `:80` site block with `redir https://{$DUCKDNS_DOMAIN}.duckdns.org:{$HTTPS_PORT}{uri} permanent`. Disable auto-redirects if needed with `auto_https disable_redirects` in global options.
**Warning signs:** Browser redirected to port 443 and connection refused.

### Pitfall 3: Stale Staging Certs Block Production Issuance
**What goes wrong:** After switching from staging to production ACME, Caddy uses cached staging certificates and doesn't request new ones.
**Why it happens:** Caddy stores certs in the `caddy_data` volume (`/data`). Staging and production certs are both stored there.
**How to avoid:** Follow the switchover procedure: `docker compose down` -> `docker volume rm <project>_caddy_data` -> change `ACME_CA` in `.env` -> `docker compose up -d`. The volume must be deleted to force fresh cert issuance.
**Warning signs:** Browser shows certificate from "Fake LE Intermediate X1" (staging CA) after switching to production.

### Pitfall 4: Module Not Registered Error
**What goes wrong:** Caddy fails to start with `module not registered: dns.providers.duckdns`.
**Why it happens:** The standard `caddy:2-alpine` image does not include the DuckDNS module. You must use the custom-built image.
**How to avoid:** Ensure `docker-compose.yml` caddy service uses `build: { dockerfile: Dockerfile.caddy }` NOT `image: caddy:2-alpine`.
**Warning signs:** Caddy container exits with module registration error.

### Pitfall 5: DNS-01 Challenge Fails Due to Token/Domain Mismatch
**What goes wrong:** ACME challenge fails with "DNS record not found" or authorization error.
**Why it happens:** The `DUCKDNS_TOKEN` does not have permission for the `DUCKDNS_DOMAIN`, or the domain is not registered on DuckDNS.
**How to avoid:** Verify the token works by testing DuckDNS API directly: `curl "https://www.duckdns.org/update?domains=nechvatal&token=<TOKEN>&txt=test&verbose=true"`. Response should include `OK`.
**Warning signs:** Caddy logs show ACME challenge failures, certificate not issued.

### Pitfall 6: Port Conflict on Host
**What goes wrong:** `docker compose up` fails with "port already in use" for port 80 or 10443.
**Why it happens:** Another service (e.g., system Caddy, Apache, nginx) is already bound to these ports on the host.
**How to avoid:** Check ports before starting: `ss -tlnp | grep -E ':80|:10443'`.
**Warning signs:** Container fails to start with bind error.

## Code Examples

Verified patterns from official sources:

### Custom Caddy Dockerfile (Dockerfile.caddy)
```dockerfile
# Source: https://hub.docker.com/_/caddy (builder variant docs)
# Source: https://caddyserver.com/docs/build
FROM caddy:2-builder-alpine AS builder

RUN xcaddy build \
    --with github.com/caddy-dns/duckdns

FROM caddy:2-alpine

COPY --from=builder /usr/bin/caddy /usr/bin/caddy
```

### Caddyfile with DNS-01 ACME + HTTP Redirect
```
# Source: https://caddyserver.com/docs/caddyfile/options
# Source: https://github.com/caddy-dns/duckdns
# Source: https://caddy.community/t/how-to-make-auto-https-redirect-to-my-custom-https-port/8051
{
    acme_ca {$ACME_CA}
    email   {$ACME_EMAIL}
}

{$DUCKDNS_DOMAIN}.duckdns.org:{$HTTPS_PORT} {
    tls {
        dns duckdns {$DUCKDNS_TOKEN}
    }

    log {
        output stderr
        level ERROR
    }

    reverse_proxy app:5000 {
        header_up Host              {http.request.host}
        header_up X-Real-IP         {http.request.remote}
        header_up X-Forwarded-For   {http.request.remote}
        header_up X-Forwarded-Proto {http.request.scheme}
    }
}

:80 {
    redir https://{$DUCKDNS_DOMAIN}.duckdns.org:{$HTTPS_PORT}{uri} permanent
}
```

### Docker Compose caddy service (updated)
```yaml
# Source: standard Docker Compose build pattern
caddy:
    build:
      context: .
      dockerfile: Dockerfile.caddy
    networks:
      - tennis_net
    ports:
      - "${HTTPS_PORT:-10443}:${HTTPS_PORT:-10443}"
      - "80:80"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
    env_file: .env
    restart: unless-stopped
    depends_on:
      app:
        condition: service_healthy
```

### .env.example additions (Phase 3)
```bash
# REQUIRED: DuckDNS domain (without .duckdns.org suffix)
DUCKDNS_DOMAIN=nechvatal

# REQUIRED: DuckDNS API token for DNS-01 ACME challenge
DUCKDNS_TOKEN=your-duckdns-token-here

# REQUIRED: Email for Let's Encrypt ACME account registration
ACME_EMAIL=your-email@example.com

# REQUIRED: ACME CA directory URL
# Staging (for testing): https://acme-staging-v02.api.letsencrypt.org/directory
# Production (for real certs): https://acme-v02.api.letsencrypt.org/directory
ACME_CA=https://acme-staging-v02.api.letsencrypt.org/directory

# HTTPS port (default: 10443)
HTTPS_PORT=10443
```

### Verify custom Caddy build includes duckdns module
```bash
docker compose exec caddy caddy list-modules | grep duckdns
# Expected output: dns.providers.duckdns
```

### Test DuckDNS token validity
```bash
curl -s "https://www.duckdns.org/update?domains=nechvatal&token=<TOKEN>&txt=test&verbose=true"
# Expected: OK
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `caddy:2.2.1-builder-alpine` | `caddy:2-builder-alpine` (resolves to 2.11.2) | Ongoing | Use floating `2-` tag for latest v2.x |
| `{env.VAR}` runtime placeholders in tls block | `{$VAR}` parse-time substitution | Always | Parse-time works everywhere; runtime only where modules support it |
| Caddy v1 websocket directive | Caddy v2 automatic WebSocket handling | Caddy v2 (2020) | No websocket directive needed; reverse_proxy handles it |
| HTTP-01 ACME challenge | DNS-01 ACME challenge | When ports 80/443 unavailable | DNS-01 works without inbound port 443; required for DuckDNS setup behind NAT |

**Deprecated/outdated:**
- `version:` key in docker-compose.yml -- already omitted in Phase 2, continue omitting
- `caddy:latest-builder` -- use `caddy:2-builder-alpine` for explicit version control

## Open Questions

1. **ACME_CA empty value handling**
   - What we know: Empty `{$ACME_CA}` causes parse error. The CONTEXT.md says "remove or empty the ACME_CA line for production."
   - What's unclear: Whether the user is open to always requiring a value (staging or production URL) instead of supporting empty/removed.
   - Recommendation: Always require `ACME_CA` to be set (staging URL or production URL `https://acme-v02.api.letsencrypt.org/directory`). This is the safest approach and still satisfies the "toggle via env var" requirement. Document this in `.env.example` with both URLs as comments.

2. **caddy_config volume**
   - What we know: `/config` stores Caddy's JSON config state. Only needed if using Caddy's API for config changes. Not needed for Caddyfile-based setups.
   - What's unclear: Whether to add it for future-proofing.
   - Recommendation: Skip it. This project uses Caddyfile exclusively. Adding it would increase complexity without benefit. If ever needed, it can be added later.

3. **Port variable in Docker Compose port mapping**
   - What we know: Docker Compose supports `"${HTTPS_PORT:-10443}:${HTTPS_PORT:-10443}"` env var syntax in port mappings.
   - What's unclear: Whether this has edge cases with docker compose interpolation.
   - Recommendation: Use it. Standard Docker Compose feature. The `:-10443` default ensures it works even without `.env`.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | none (default pytest discovery) |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HTTP-01 | Custom Caddy image builds and includes duckdns module | smoke (Docker) | `docker compose build caddy && docker compose run --rm caddy caddy list-modules \| grep duckdns` | No -- Wave 0 (manual/script) |
| HTTP-02 | HTTPS serves valid certificate via DNS-01 | smoke (integration) | `docker compose up -d && curl -k -s -o /dev/null -w '%{http_code}' https://localhost:10443/health` | No -- Wave 0 (manual verify) |
| HTTP-03 | WebSocket passes through Caddy over HTTPS | smoke (integration) | Manual: open browser, verify Socket.IO connects via wss:// | No -- manual-only (requires browser + real WebSocket) |
| HTTP-04 | ACME_CA env var toggles staging/production | smoke (config) | `docker compose exec caddy caddy environ \| grep ACME_CA` | No -- Wave 0 (manual verify) |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q` (existing unit tests still pass)
- **Per wave merge:** `docker compose build && docker compose up -d` + manual HTTPS verification
- **Phase gate:** Staging cert issued, HTTP redirect works, WebSocket connects over wss://

### Wave 0 Gaps
- [ ] No new automated test files needed -- Phase 3 validation is infrastructure-level (Docker build + ACME issuance), not unit-testable
- [ ] Smoke tests are checkpoint:human-verify style (as established in Phase 1-2)
- [ ] DuckDNS token validity check: `curl` command in plan verification steps

*(Phase 3 is infrastructure configuration, not application code. Validation is via Docker build success, `caddy list-modules`, HTTPS connectivity, and manual browser verification. No pytest test files are appropriate.)*

## Sources

### Primary (HIGH confidence)
- [Caddy Official Docker Hub](https://hub.docker.com/_/caddy) -- builder image tags, multi-stage build pattern, version 2.11.2 confirmed
- [Caddy Build from Source docs](https://caddyserver.com/docs/build) -- xcaddy `--with` syntax, Docker build example
- [caddy-dns/duckdns README](https://github.com/caddy-dns/duckdns/blob/master/README.md) -- `dns duckdns {$TOKEN}` syntax, `override_domain`, `resolver` options
- [Caddy Global Options docs](https://caddyserver.com/docs/caddyfile/options) -- `acme_ca`, `email`, `acme_dns` global options
- [Caddy TLS directive docs](https://caddyserver.com/docs/caddyfile/directives/tls) -- `dns` subdirective, `ca` subdirective, `issuer` syntax
- [Caddy Concepts docs](https://caddyserver.com/docs/caddyfile/concepts) -- `{$ENV}` parse-time substitution, `{$ENV:default}` syntax, empty var behavior
- [Caddy Automatic HTTPS docs](https://caddyserver.com/docs/automatic-https) -- default CAs (Let's Encrypt + ZeroSSL), auto-redirect behavior

### Secondary (MEDIUM confidence)
- [Caddy Community: Auto-HTTPS redirect to custom port](https://caddy.community/t/how-to-make-auto-https-redirect-to-my-custom-https-port/8051) -- confirmed auto-redirect omits non-standard port; manual redirect required
- [Caddy Community: Caddy Docker with DuckDNS](https://caddy.community/t/caddy-docker-with-duckdns/18682) -- practical Docker Compose + Caddyfile examples verified against official docs
- [Caddy Community: Let's Encrypt staging](https://caddy.community/t/how-to-use-lets-encrypt-staging-endpoint-with-caddy/18514) -- staging global option usage confirmed
- [Caddy Community: Errors using env vars](https://caddy.community/t/errors-using-environment-variable-s-in-caddyfile/21347) -- empty `acme_ca` parse error confirmed

### Tertiary (LOW confidence)
- [Caddy Community: HTTPS on non-standard port](https://caddy.community/t/caddy-for-https-on-non-standard-port/23848) -- DNS challenge recommended for non-standard ports (aligns with our approach)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- official Docker images, official xcaddy build tool, well-documented module
- Architecture: HIGH -- patterns verified against official docs and multiple community examples
- Pitfalls: HIGH -- parse error confirmed by community reports; auto-redirect port omission confirmed by Caddy developer response
- ACME_CA handling: MEDIUM -- the "always set" approach is recommended but diverges slightly from CONTEXT.md "remove or empty" language

**Research date:** 2026-03-19
**Valid until:** 2026-04-19 (Caddy ecosystem is stable; v2.11.x unlikely to break patterns)
