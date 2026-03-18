# Codebase Concerns

**Analysis Date:** 2026-03-18

## Tech Debt

**Hardcoded Rank Limits and Magic Numbers:**
- Issue: Rank limit of 45 is hardcoded throughout the codebase as the maximum pyramid size. Also hardcoded initial rank 99 for new players waiting to be placed.
- Files: `app.py` (lines 712, 778-783, 1678, 1721-1724, 2093-2095, 2185-2187)
- Impact: Making the pyramid larger or changing ranking logic requires multiple code changes and risk of inconsistency. The rank 45 and rank 99 values appear in 10+ locations.
- Fix approach: Extract to module-level constants (`MAX_RANK = 45`, `PENDING_PLAYER_RANK = 99`) and reference throughout.

**Hardcoded Default Passwords:**
- Issue: Default passwords are hardcoded in plain text in code: `"DefaultPassword1!"` and `"PasswordForNewPlayer123!"`
- Files: `app.py` (lines 1864, 1942, 2115)
- Impact: Passwords are committed to git history, visible in logs, and if exposed creates security vulnerability. Should be generated or configuration-based.
- Fix approach: Generate cryptographically secure random passwords or move to configuration. At minimum, document password policy in environment config.

**Monolithic Application Structure:**
- Issue: All application logic (database, routing, business logic, WebSocket handlers) is in a single 2,559-line file `app.py`.
- Files: `app.py`
- Impact: Hard to test individual components, difficult to navigate code, high complexity per file, challenging to maintain.
- Fix approach: Refactor into modules: `db.py` (database operations), `routes.py` (Flask routes), `business.py` (ranking/challenge logic), `socketio_handlers.py` (WebSocket events).

**Date/Time Parsing Fragility:**
- Issue: Datetime strings are parsed repeatedly using `.split(".")[0]` to strip milliseconds before `strptime()`. This pattern appears 15+ times.
- Files: `app.py` (lines 270-271, 303-304, 320-321, 340-341, 615-616, 651-652, 679-680, etc.)
- Impact: If timestamp format changes (e.g., to ISO8601 with timezone), all these locations must be updated. Inconsistent handling makes bugs likely.
- Fix approach: Create utility function `parse_datetime_string(dt_str)` that handles all parsing with consistent error handling.

**Silent Exception Handling:**
- Issue: Several places catch exceptions but only pass without logging or handling.
- Files: `app.py` (lines 902, 911, 1236, 1250, 1398, 1423, 1839)
- Impact: Bugs silently fail, making debugging difficult. State may be inconsistent without awareness.
- Fix approach: Replace bare `pass` statements with logging and fallback values where appropriate. All exception handling should at minimum log what happened.

## Security Concerns

**Default Secret Key in Development:**
- Risk: Default Flask `SECRET_KEY` is `"a-very-long-and-super-secret-key-for-dev"` if environment variable not set. This is committed to repo.
- Files: `app.py` (lines 83-89)
- Current mitigation: Warning logged at startup, but key is still weak.
- Recommendations: Fail loudly if SECRET_KEY not set in production. Generate strong random key at startup for development. Never commit weak keys.

**CORS Misconfiguration:**
- Risk: CORS is set to `"*"` (allow all origins) with warning log but no blocking. This allows any website to access the application.
- Files: `app.py` (lines 95-225)
- Current mitigation: Warning logged, but configuration allows it.
- Recommendations: Fail startup if `CORS_ALLOWED_ORIGINS` not set in production. Disable CORS for non-debug modes unless explicitly configured.

**Password Hashing Uses `bcrypt.gensalt()` Without Rounds Specification:**
- Risk: `bcrypt.gensalt()` uses default rounds (currently 12), but explicit rounds specification is more secure and controllable.
- Files: `app.py` (lines 413, 1865-1866, 2116-2117, 2412)
- Current mitigation: bcrypt library default is reasonable, but not explicit.
- Recommendations: Use `bcrypt.gensalt(rounds=12)` explicitly throughout for auditability and control.

**Privilege Level String Comparison:**
- Risk: Access control uses string matching on `privilege_level` field (`"admin"`, `"superadmin"`, `"player"`). Typos or case sensitivity issues could create security holes.
- Files: `app.py` (lines 159-175)
- Current mitigation: Consistent string usage observed, but error-prone pattern.
- Recommendations: Use enum class for privilege levels or create constants: `PRIVILEGE_PLAYER = "player"`, `PRIVILEGE_ADMIN = "admin"`, etc.

**No CSRF Token Validation in Some Routes:**
- Risk: Flask-WTF CSRF protection is initialized (`CSRFProtect(app)`) but not explicitly validated on all POST/PUT/DELETE routes.
- Files: `app.py` (CSRF initialized line 22, but many routes lack `@csrf.protect`)
- Current mitigation: Flask-WTF may validate by default, but not explicit.
- Recommendations: Audit all mutation routes to ensure `@csrf.protect` decorator or explicit token validation.

**Rate Limiting Only on Login:**
- Risk: Rate limiting implemented for login attempts, but no rate limiting on other endpoints. Admin endpoints could be brute-forced or abused.
- Files: `app.py` (lines 1038-1055)
- Current mitigation: Dictionary-based in-memory tracking for login only.
- Recommendations: Implement rate limiting decorator for all API endpoints. Use persistent store (Redis) instead of in-memory dictionary for multi-instance deployments.

## Performance Bottlenecks

**In-Memory Cache Invalidation Issue:**
- Problem: `DataCache` class uses simple TTL but invalidation is manual via `emit_data_update()`. Multiple places call `data_cache.invalidate()` but coverage may be incomplete.
- Files: `app.py` (lines 228-256, 948-951)
- Cause: No automatic cache invalidation on database modifications. If cache invalidation call is missed, stale data is served.
- Improvement path: Either (1) use request-scoped caching, or (2) wrap all database mutations with automatic cache invalidation, or (3) switch to Redis-backed cache with pub/sub invalidation.

**Eligible Opponents Loop with Database Queries:**
- Problem: `eligible_opponents_for()` function contains a while loop that re-queries database to check unavailable player counts.
- Files: `app.py` (lines 720-737)
- Cause: Multiple sequential queries in loop, potentially 3-5 database round-trips per eligibility check.
- Improvement path: Fetch all unavailable counts in single query, then process in memory.

**Player Reranking Deletes Rank > 45:**
- Problem: `rerank_players()` calls `DELETE FROM players WHERE rank > 45` to enforce pyramid limit, but this happens after EVERY admin operation.
- Files: `app.py` (lines 765-791)
- Cause: No batch deletion or optimization; rows are deleted individually by rank filter.
- Improvement path: Pre-calculate which players to delete before re-ranking, or use LIMIT clause in delete.

**SocketIO Broadcasting to All Clients:**
- Problem: `emit_data_update()` broadcasts full dataset to all connected clients on every change.
- Files: `app.py` (lines 953-977)
- Cause: No selective emission or incremental updates; always sends complete state.
- Improvement path: Send only changed data (delta updates) or limit broadcast to affected clients only.

**N+1 Query in Challenge Serialization:**
- Problem: `serialize_challenge()` is called for each challenge, which performs datetime parsing repeatedly.
- Files: `app.py` (lines 286-353)
- Cause: Could be optimized with single database query that pre-formats all datetimes.
- Improvement path: Move datetime formatting to SQL query or batch-format all challenges at once.

## Fragile Areas

**Challenge Result Submission Logic:**
- Files: `app.py` (lines 1625-1766)
- Why fragile: Complex state transitions involving rank updates, block status changes, new player handling, and deletion of rank 45 player. Multiple conditional branches (challenger wins, opponent wins, not happened) with side effects. One error cascades.
- Safe modification: Add comprehensive logging at each state transition. Write tests for all three result types, including edge cases (new player losing, rank overflow, etc.). Use transaction boundaries carefully.
- Test coverage: No test files found for this critical logic.

**Datetime String Parsing in Multiple Formats:**
- Files: `app.py` (multiple locations)
- Why fragile: Code assumes datetime strings are in format `YYYY-MM-DD HH:MM:SS` with optional microseconds. If database schema changes or external data has different format, parsing fails silently.
- Safe modification: Create single `parse_datetime_string()` utility with comprehensive tests. Use ISO8601 format consistently.
- Test coverage: No unit tests found for datetime parsing.

**Rank Calculation with Unavailable Players:**
- Files: `app.py` (lines 667-762)
- Why fragile: Logic expands eligible opponent range if unavailable players exist in original range. This is clever but complex. If business rules change (e.g., unavailable player blocking rules), many conditions must be updated.
- Safe modification: Add comments explaining each rank range bucket (11-15, 16-21, etc.) and why it exists. Refactor into lookup table or configuration. Add tests covering unavailable player scenarios.
- Test coverage: No tests found.

**Login Attempt Tracking Dictionary:**
- Files: `app.py` (lines 1038-1054)
- Why fragile: In-memory dictionary `login_attempts` is never cleaned up. Old entries accumulate indefinitely, consuming memory. In multi-instance deployment, each instance has separate dictionary (no shared state).
- Safe modification: Add cleanup job (every hour) to prune old entries. Use Redis for shared state. Add tests for lockout timing and reset logic.
- Test coverage: No tests found.

## Scaling Limits

**In-Memory Login Attempt Tracking:**
- Current capacity: Dictionary stores one entry per failed login attempt forever
- Limit: Memory leaks over time; in production with many users, grows unbounded
- Scaling path: (1) Implement periodic cleanup, (2) use Redis, (3) set max dictionary size with LRU eviction.

**SQLite Database:**
- Current capacity: Tennis database is 61KB; single file, local filesystem
- Limit: SQLite has file-level locking; concurrent write operations will block. Not suitable for high-concurrency scenarios.
- Scaling path: If pyramid grows beyond 45 players or concurrent users increase significantly, migrate to PostgreSQL with connection pooling.

**Single-Process Flask with Eventlet:**
- Current capacity: Eventlet provides async I/O within single process; can handle ~1000 concurrent WebSocket connections
- Limit: Single CPU core; no built-in horizontal scaling
- Scaling path: Deploy with Gunicorn + multiple workers, load balancer, and shared session/cache backend (Redis).

**Data Cache in Memory:**
- Current capacity: DataCache stores multiple full player/challenge datasets in memory (10-second TTL)
- Limit: Not shared between processes; each Gunicorn worker has separate cache
- Scaling path: Switch to Redis-backed cache, or use session-scoped caching instead of request-scoped.

## Dependencies at Risk

**Flask-SocketIO with Eventlet:**
- Risk: Eventlet is a greenlet-based concurrency library. Mixing Eventlet with certain libraries (e.g., requests library without monkey-patching) can cause hangs.
- Impact: WebSocket connections may hang or timeout. Debugging asyncio issues is complex.
- Migration plan: If stability becomes an issue, migrate to `python-socketio` with `aiohttp` backend, or use Gevent instead of Eventlet.

**Flask-Login User Session Management:**
- Risk: Flask-Login stores user ID in Flask session, which defaults to secure cookie storage. If SECRET_KEY is weak, session can be forged.
- Impact: Authentication bypass if SECRET_KEY is compromised.
- Migration plan: No immediate migration needed if SECRET_KEY is strong. Consider session backend (Redis) for persistence across server restarts.

**Outdated or Large Dependency Set:**
- Risk: `requirements.txt` is very large (150+ packages), including many development tools (black, flake8, pytest, ipython, mypy). Production should only include runtime dependencies.
- Impact: Bloated Docker image, larger attack surface, slower pip install.
- Migration plan: Create separate `requirements.txt` (prod) and `requirements-dev.txt` (dev). `prod-requirements.txt` already exists but may not be complete.

## Test Coverage Gaps

**No Unit Tests:**
- What's not tested: Database functions (`get_active_challenges()`, `eligible_opponents_for()`, `rerank_players()`), ranking logic, challenge result submission, new player handling
- Files: `app.py` (all database and business logic functions)
- Risk: Ranking logic bugs go undetected until production. New features break existing behavior without immediate feedback.
- Priority: **High** - Core business logic has zero test coverage

**No Integration Tests:**
- What's not tested: Full challenge workflow (create, resolve, update ranks), multi-player rank cascades, new player lifecycle
- Risk: Complex interactions between tables (challenges, players, blocks) are untested
- Priority: **High** - Business-critical workflows need testing

**No Frontend/E2E Tests:**
- What's not tested: Web UI interactions, WebSocket real-time updates, form submission, authentication flows
- Risk: UI bugs and regressions are caught only manually
- Priority: **Medium** - Users will find bugs first

**No Login/Authentication Tests:**
- What's not tested: Password hashing, bcrypt verification, rate limiting, privilege level checks, password change flows
- Files: `app.py` (lines 1029-1110, 2384-2442)
- Risk: Authentication bypass or privilege escalation bugs could go undetected
- Priority: **High** - Security-critical

**No Database Error Handling Tests:**
- What's not tested: Database connection failures, transaction rollbacks, constraint violations
- Risk: Silent failures or partial state corruption during error conditions
- Priority: **Medium** - Error paths should work correctly

## Known Issues and Observations

**Privilege Level Not Used Consistently:**
- Observation: `privilege_level` field exists in schema but is set to hardcoded `"player"` for all new players. Never updated except via admin interface.
- Impact: Cannot distinguish between regular players and admins based on database alone; must use login state.

**Block Duration Logic Unclear:**
- Observation: Players can be blocked as "challenger" (cannot initiate challenges) or "opponent" (cannot be challenged). Block bits are set separately but cleared together in some places (line 2354, 2360).
- Impact: Confusing behavior where clearing one type might clear the other unexpectedly.

**Username Generation Not Predictable:**
- Observation: Username generated from player name + current timestamp (`new_name.replace(" ", "") + str(int(time.time()))`)
- Impact: Usernames not deterministic or human-readable. Could collide if two players added in same second.

---

*Concerns audit: 2026-03-18*
