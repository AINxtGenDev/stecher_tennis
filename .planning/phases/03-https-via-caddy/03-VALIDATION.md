---
phase: 03
slug: https-via-caddy
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-19
---

# Phase 03 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (existing) |
| **Config file** | `pytest.ini` (existing from Phase 1) |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~3 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `docker compose build && docker compose up -d` + manual HTTPS verify
- **Before `/gsd:verify-work`:** Full suite must be green + staging cert issued
- **Max feedback latency:** 5 seconds (pytest) / 60 seconds (Docker build)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | HTTP-01 | smoke (Docker) | `docker compose build caddy` | N/A (Dockerfile) | ⬜ pending |
| 03-01-02 | 01 | 1 | HTTP-01 | smoke (Docker) | `docker compose run --rm caddy caddy list-modules \| grep duckdns` | N/A | ⬜ pending |
| 03-02-01 | 02 | 2 | HTTP-02 | smoke (integration) | `curl -k -s -o /dev/null -w '%{http_code}' https://localhost:10443/health` | N/A | ⬜ pending |
| 03-02-02 | 02 | 2 | HTTP-03 | manual | Browser: verify Socket.IO connects via wss:// | N/A | ⬜ pending |
| 03-02-03 | 02 | 2 | HTTP-04 | smoke (config) | `docker compose exec caddy caddy environ \| grep ACME_CA` | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.*

Phase 3 is infrastructure configuration (Docker build + Caddyfile + ACME). No new pytest test files are appropriate — validation is via Docker build success, module listing, HTTPS connectivity, and manual browser verification (consistent with Phase 1-2 smoke test pattern).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| WebSocket connects over wss:// | HTTP-03 | Requires browser + real WebSocket handshake | 1. Open browser to `https://nechvatal.duckdns.org:10443` 2. Login 3. Verify real-time updates appear (Socket.IO connected) |
| Staging cert issued with correct CA | HTTP-02 | Requires TLS inspection | `curl -vk https://localhost:10443/health 2>&1 \| grep issuer` — should show "Fake LE" for staging |
| HTTP redirect includes port | HTTP-02 | Requires redirect inspection | `curl -sI http://localhost/health` — Location header must include `:10443` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
