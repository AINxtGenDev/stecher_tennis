---
phase: 1
slug: app-container
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-18
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (installed in conda env; no test files exist yet) |
| **Config file** | none — Wave 0 creates `pytest.ini` |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | CONT-01 | smoke | `docker build -t tennis-test . && docker image inspect tennis-test --format='{{.Size}}'` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | CONT-02 | smoke | `docker run --rm tennis-test whoami` | ❌ W0 | ⬜ pending |
| 01-01-03 | 01 | 1 | CONT-03 | unit | `pytest tests/test_dockerignore.py` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 1 | CONT-04 | smoke | `docker run --rm -e DB_PATH=/tmp/test.db tennis-test python -c "from app import app; print(app.config['DATABASE'])"` | ❌ W0 | ⬜ pending |
| 01-02-02 | 02 | 1 | OPS-01 | unit | `pytest tests/test_health.py -x -q` | ❌ W0 | ⬜ pending |
| 01-02-03 | 02 | 1 | OPS-02 | smoke | `docker run -d tennis-test && docker logs ... \| grep "Using worker: eventlet"` | ❌ W0 | ⬜ pending |
| 01-02-04 | 02 | 1 | OPS-03 | smoke | `docker logs <container>` captures app logs | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_health.py` — stubs for OPS-01: `/health` returns 200, no auth, CSRF-exempt
- [ ] `tests/test_db_path.py` — stubs for CONT-04: `DB_PATH` env var sets database path, parent dir auto-created
- [ ] `tests/conftest.py` — Flask test client fixture, temporary DB fixture
- [ ] `pytest.ini` — test discovery config
- [ ] Framework install: already in conda env; `docker-requirements.txt` does not need pytest (dev-only)

*pytest is already installed in the conda environment.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Image size < 200MB | CONT-01 | Requires full `docker build` | `docker build -t tennis-test . && docker image inspect tennis-test --format='{{.Size}}'` |
| Non-root process | CONT-02 | Requires running container | `docker run --rm tennis-test whoami` → expect `appuser` |
| Gunicorn 1 worker + eventlet | OPS-02 | Requires running container | `docker run -d tennis-test && docker logs <id>` → check for "1 worker" and "eventlet" |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
