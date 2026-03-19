---
phase: 4
slug: multi-arch-rpi-deploy
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-19
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (existing) |
| **Config file** | pytest.ini (existing) |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~2 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | CONT-05 | smoke/manual | `docker buildx build --platform linux/amd64,linux/arm64 --push .` | N/A — build script IS the test | ⬜ pending |
| 04-01-02 | 01 | 1 | CONT-05 | smoke/manual | `ssh stecher "cd ~/stecher_tennis && docker compose ps"` | N/A — deploy script verifies | ⬜ pending |
| 04-01-03 | 01 | 1 | CONT-05 | smoke/manual | `curl -s https://nechvatal.duckdns.org:10443/health` | N/A — deploy script verifies | ⬜ pending |
| 04-01-04 | 01 | 1 | CONT-05 | smoke/manual | Container restart + data check | N/A — manual verification | ⬜ pending |
| 04-01-05 | 01 | 1 | CONT-05 | smoke/manual | `ssh stecher "sudo reboot"` + wait + verify | N/A — manual verification | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No new automated test files needed — this phase is primarily shell scripts and Docker config changes. Validation is inherently manual/smoke-test based (SSH to RPi, verify services, check certificates).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Multi-arch build completes | CONT-05 | Requires QEMU + buildx + GHCR push | Run `build-and-push.sh`, verify both platforms in GHCR manifest |
| App runs on RPi | CONT-05 | Requires physical Raspberry Pi | SSH to RPi, check `docker compose ps`, curl /health |
| HTTPS with production cert | CONT-05 | Requires DNS + real ACME cert | `curl -s https://nechvatal.duckdns.org:10443/health` from external |
| Data persists across restart | CONT-05 | Requires stateful Docker restart cycle | Restart containers, verify SQLite data still present |
| WebSocket connects | CONT-05 | Requires browser or upgrade-header test | Open app in browser, check Socket.IO connects |
| Containers restart after reboot | CONT-05 | Requires RPi reboot cycle | `ssh stecher "sudo reboot"`, wait, verify containers running |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
