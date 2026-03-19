---
phase: 2
slug: compose-stack
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-19
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (existing) |
| **Config file** | `pytest.ini` (testpaths = tests) |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~3 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run full docker smoke test sequence (COMP-01 through COMP-04)
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds (pytest); ~60 seconds (docker smoke)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | COMP-01 | smoke | `docker compose up -d && docker compose ps` | N/A (manual) | ⬜ pending |
| 02-01-02 | 01 | 1 | COMP-02 | smoke | `curl http://localhost/health` succeeds; `curl http://localhost:5000/health` fails | N/A (manual) | ⬜ pending |
| 02-01-03 | 01 | 1 | COMP-03 | smoke | Manual: create data, down, up, verify | N/A (manual) | ⬜ pending |
| 02-02-01 | 02 | 1 | COMP-04 | review | `cat .env.example` | N/A (manual) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers Phase 1 unit tests. Phase 2 tests are smoke/integration tests performed manually during plan execution, not new pytest files.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Both services start | COMP-01 | Requires running Docker stack | `docker compose up -d && docker compose ps` — both show "Up"/"healthy" |
| App port isolated | COMP-02 | Network-level check | `curl http://localhost/health` returns 200; `curl http://localhost:5000/health` fails/times out |
| Data persists | COMP-03 | Requires state modification + restart cycle | Create data via app, `docker compose down && docker compose up -d`, verify data still present |
| Env vars documented | COMP-04 | Human review of completeness | Compare `.env.example` vars against CLAUDE.md env var list |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
