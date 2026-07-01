# Session Checkpoint

**Date:** 2026-07-01
**Branch:** docker
**Version:** 3.68 — **live on TEST (nechvatal)**; PROD (tc-breakpoint) still on 3.67
**Git Status:** `docker`; untracked: `REVIEW*.md`, `02_tennislogo.png` (root source), `tennis.db.prev-36players`, `tennis.db.pretest-tiebreak` (local DB backups)
**⚠️ DEPLOYMENT ROLES (corrected by user 2026-06-25 — overrides older entries below):**
- **PRODUCTION (club TC Breakpoint):** `tc-breakpoint-rangliste.duckdns.org:10445` on RPi 5 @ `192.168.1.180` (ssh `stechertennis`). Be careful — live club.
- **TEST system:** `nechvatal.duckdns.org` on RPi 5 @ `192.168.1.213` (ssh `stecher`). Safe to deploy/experiment. **v3.67 live here.**
  (Earlier checkpoint called nechvatal "Production #1" — that label is now stale.)

## Current Session (2026-07-01) — Footer TC Breakpoint logo + v3.68

Small template/asset change on the logged-in `/index` footer. **Code only — not built or deployed;
TEST + PROD still run 3.67.**

### What changed
- **`static/02_tennislogo.png`** (new) — copied from repo-root `02_tennislogo.png` (the "tc breakpoint
  leopoldsdorf" wordmark, 1921×819). Served by Flask from `/static/`.
- **`templates/index.html`** — added the logo to the footer at the **bottom-left**, mirroring the existing
  duck logo's spacing (`position: absolute; bottom: 15px; left: 15px`). Height matched to the duck (46px);
  width 108px to preserve the 2.35:1 aspect ratio. Wrapped in `<a href="https://tc-breakpoint.at/"
  target="_blank" rel="noopener">` so it opens the club homepage in a new tab.
- **Version bump 3.67 → 3.68**: footer string `Version: 3.68 • 01. Juli 2026` + `APP_VERSION` in `app.py`.
- **Copyright** `© 2025 → © 2026 Matthias Stecher` in the footer (only occurrence in templates).

### Verified
- Ran the app locally (`FLASK_PORT=5055 python app.py`), logged in as MStecher (superadmin), screenshotted
  the `/index` footer: tennis logo bottom-left, duck bottom-right, `Version: 3.68 • 01. Juli 2026` centered,
  logo `<a>` points to `https://tc-breakpoint.at/`. Layout matches the mirrored-spacing intent.
- **Login note:** local `tennis.db` is the throwaway test-mutated copy; its MStecher password is unknown, so
  the screenshot used a **temporary** bcrypt password that was **restored to the original hash afterward**
  (no lasting DB change).

### Known cosmetic issue
- The logo PNG has a **non-transparent light-gray background**, so it shows a faint rectangle against the
  footer's `#f8f9fa`. Blending seamlessly needs a transparent-background version of the image (not done).

### `/index` footer + `/rangliste` header both carry the logo now
- **`/index`** footer (logged-in): logo bottom-left (see above).
- **`/rangliste`** (public) header: logo added in the yellow `.ranking-header` (`#f8e473`) on the **left**,
  title/badge stay centered (logo is `position: absolute` on desktop). Committed separately (see next entry).

### `/rangliste` header logo — responsive + spinning (commit follows)
- **Placement:** logo in the yellow header. Desktop 90px on the left; ≤900px 55px; **phones ≤600px it stacks
  centered above the title** (`position: static; width: fit-content; margin: 0 auto`) so it never overlaps the
  centered title; phone-landscape 38px back on the left.
- **Why the stack-on-phone:** first attempt hid the logo `<600px` (`display:none`) to avoid title overlap →
  user reported it **missing on their Android phone**. Fixed by showing it centered-on-top instead of hiding.
- **Spin:** the `<img>` is wrapped in a `.club-logo` div (positioning) so the spin animation doesn't fight the
  positioning `transform`. Inner img: `animation: logo-spin-y 8s linear infinite` (`rotateY 0→360°`),
  `perspective: 600px` on the wrapper for real 3D; `prefers-reduced-motion` opt-out. Verified live: matrix
  advances ~360°/8s. Note: being a flat image, half of each turn shows the **mirrored back face** (expected
  for a 360° Y spin — user confirmed "perfect").
- **Not a link** on `/rangliste` (unlike the `/index` footer logo, which links to `https://tc-breakpoint.at/`).

### Build + deploy (TEST) — v3.68
- **arm64-only app-image build** (`docker buildx --builder multiarch --platform linux/arm64 ... --push`),
  skipping Caddy (unchanged). Pushed `:v3.68` + `:latest`, manifest list `sha256:ef0e91e4538d…`.
- Deployed to nechvatal (`ssh stecher`, `docker compose pull app && up -d app`) — only the app container
  recreated; caddy/backup untouched, `tennis_data` volume persisted.
- **Verified:** app **healthy**, startup log `version: 3.68`, running digest `ef0e91e4538d` = pushed manifest;
  internal HTTPS (`curl --resolve`) `/rangliste` → 200, `/login` → 200, `/static/02_tennislogo.png` → 200.
- Confirmed box identity first: `ssh stecher` = TEST `192.168.1.213`, was on 3.67 (digest 0dfca9820f65).
- **PROD (tc-breakpoint) left on 3.67** — not deployed.

### Next
- Verify `/rangliste` on a real phone via the TEST URL (`https://nechvatal.duckdns.org:10443/rangliste`):
  spinning logo, phone-centered placement, no title overlap.
- Deploy v3.68 to **PROD** (tc-breakpoint) when ready.
- Optional: supply/produce a transparent-background logo to drop the gray box.

## Current Session (2026-06-26, later) — Hourly local DB backup (sidecar) → TEST + PROD

Built and deployed an automated, transaction-safe, versioned, self-verifying **hourly local
backup** of the SQLite DB. Commit `11031e7` on `docker` (pushed). Live on **both** boxes.

### What was added
- **`backup_db.py`** (repo root, stdlib-only) — uses the SQLite **Online Backup API**
  (`Connection.backup`, same primitive as `app.py:export_database`), never a file copy.
  Per run: snapshot → verify the *copy* (`integrity_check` + `foreign_key_check` + players≥1 +
  view selectable + 20 KB floor) → SHA-256 sidecar → **atomic rename** publish → fsync →
  tiered promote/prune. Modes: default one-shot, `--loop` (sidecar), `--restore-test`,
  `--healthcheck`. Daily automated restore test proves recoverability.
- **`docker-compose.yml`** — new **`backup` sidecar** reusing the app image (NO rebuild):
  `entrypoint: python /app/backup_db.py --loop`. Mounts `tennis_data:/app/data` **RW** (WAL
  needs `-shm`; backup only reads), `./backups:/backups` (host bind-mount, **outside** the live
  volume = DR isolation), and bind-mounts `backup_db.py` `:ro`. Hardened like app/caddy
  (`read_only`, `cap_drop: ALL`, tmpfs `/tmp`). Docker `healthcheck` → **unhealthy if no
  success in 75 min**.
- **Retention (tiered, env-tunable):** `hourly/` 48 (2 d), `daily/` 30 (first/day), `weekly/`
  12 (Mondays). Filenames `tennis-YYYYMMDDTHHMMSSZ.db` (UTC, sortable, unique) + `.sha256`.
- **Monitoring:** per-run log → stdout + `backups/backup.log`; `backups/status.json` heartbeat
  (last_success_utc, consecutive_failures, last_restore_test_date). **Alert hook
  `BACKUP_ALERT_CMD` left empty/pluggable** (user choice: log+healthcheck for now).
- **`documentation/db-backup-plan.md`** — full design + ops + manual restore drill.
- `.gitignore`: added `backups/`.

### Verified
- **Local** (DB copy, scratchpad): backup ok, restore-test PASS, healthcheck=0; **negative
  tests all caught** (missing source→fail+alert, corrupt backup→checksum-mismatch fail, stale
  heartbeat→healthcheck=1). Fixed one robustness bug (write_status now `makedirs(BACKUP_DIR)`).
- **TEST (nechvatal, .213, port 10443):** `git pull && mkdir backups && compose up -d` — only
  the backup service created, app/caddy untouched. Backup of live DB (41 players, 125 ch) +
  restore-test PASS; sidecar **healthy**.
- **PROD (tc-breakpoint, .180, port 10445 — LIVE CLUB):** same deploy; backup of live DB (39
  players, 125 ch) + restore-test PASS; sidecar **healthy**; **`/login` still HTTP 200** (app
  never blocked). Box git was clean FF; box user is uid 1000 = container appuser (no chown).

### PROD app updated 3.63 → 3.67 (user did phone check first)
- PROD was running **v3.63** (Jun 18 stand-up); TEST already on 3.67. User confirmed phone check,
  then asked to deploy latest to PROD **keeping the existing player DB**.
- Pre-flight: explicit verified backup `tennis-20260626T181409Z.db` (sha256 `98d60020…`) on host;
  recorded live state **39 players, 125 challenges, rank1 Patrick Krauskopf**.
- `docker compose pull app && up -d app` — recreated only the app container; `tennis_data` volume
  persisted; `init_db()` idempotent (no reseed). caddy/backup untouched.
- **Verified:** version **3.67**, image digest `0dfca982…` (= TEST), app healthy; DB **intact &
  identical** (39/125/Patrick Krauskopf, `integrity_check=ok`); `/login` + `/rangliste` → 200.
- Both boxes now fully aligned: **app 3.67 + hourly backup sidecar**.

### Off-box backup replication PROD → TEST (commit `c25c9a1`)
- **Why:** local backups + live DB sat on the same RPi SSD — single-disk failure lost both.
- **What:** PROD host-level `rsync -a --delete` mirrors `backups/` → TEST
  `~/offsite-backups/from-tc-breakpoint/` over the LAN (192.168.1.213:10115).
- **Auth (locked down):** dedicated `~/.ssh/offsite_backup` ed25519 key on PROD; TEST
  `authorized_keys` entry `command="/usr/bin/rrsync -wo …",restrict,from="192.168.1.180"` —
  rsync-write-only into that one dir, only from PROD's IP, no shell. **Verified** an arbitrary
  command is rejected (`rrsync error: SSH_ORIGINAL_COMMAND does not run rsync`).
- **Schedule:** systemd timer `tennis-backup-sync.timer` on PROD, hourly at `:10`,
  `Persistent=true`, runs `sync_backups_offsite.sh` (in repo) as `User=stecher`. Units live in
  `/etc/systemd/system/` (host-specific, not in git; content in `documentation/db-backup-plan.md`).
- **Observability:** `backups/sync.log` + `backups/sync_status.json` on PROD; `journalctl -u
  tennis-backup-sync`. First manual run = success; mirror confirmed on TEST.
- **Mirror semantics:** `--delete` = exact bounded replica; dead source can't run sync → no
  empty-mirror propagation. **TEST → PROD reverse NOT set up** (test data lower priority).

### Docs (commit `c5e3e3e`)
- **README.md**: "Installation & Setup" trimmed to **Docker-only** (removed conda/venv local-install
  + pip dep list; local dev still under Development). New **"Database Backups"** section inside Docker
  Deployment (sidecar mechanism + the `backups/` path & tiered layout + off-box PROD→TEST replication).
  Recent-Changes 2026-06-26 entry. Anchors verified, code fences balanced. (LOC table left stale.)
- `documentation/db-backup-plan.md` = full design/ops reference (also covers off-site sync).

### Reboot survival re-verified on PROD (after adding backup sidecar + timer)
- Actually rebooted PROD (boot_id `e6e4be22…`→`235df7e6…`, new uptime 2026-06-26 20:46:21); **back in ~25s**.
- Self-healed with zero manual steps: Docker `enabled`; **app/caddy/backup** all Up/healthy within ~8s;
  backup sidecar auto-ran a fresh post-boot backup (18:46:30Z); offsite **timer enabled+active**, re-armed
  (next 21:10 CEST); `Persistent` correctly did NOT spurious-fire (no run missed in the 25s window);
  `/login` → 200. Safety backup taken pre-reboot (`tennis-20260626T184558Z.db`).
- **Offsite timer fire CONFIRMED** (post-reboot): systemd auto-triggered the service at 21:10:22 CEST
  (journal `Starting → offsite sync ok → Finished`, not a manual run); `sync_status.json` last_run
  `19:10:23Z`; timer re-armed `NEXT 22:10 CEST`. Proves scheduling + reboot-survival together.

### Commits this session (branch `docker`, all pushed)
- `11031e7` feat: hourly transaction-safe local DB backup sidecar
- `c25c9a1` feat: off-box backup mirror PROD → TEST (restricted rrsync key + systemd timer)
- `c5e3e3e` docs: README Docker-focused Install + Database Backups section
- `8291ab8` docs: checkpoint (backup + off-box + README)
- `213ea59` docs: checkpoint (PROD reboot survival re-verified)
- `12f0c77` docs: checkpoint (offsite timer fire confirmed, post-reboot)
- `2d91581` docs: checkpoint (end-of-session branch state)
- `24065ef` docs: optimize CLAUDE.md (accurate Docker deploy + backup system + greppable app.py map)
- PROD app updated 3.63 → **3.67** live (no commit — image pull only); player DB verified identical.
- PROD rebooted for survival re-verification (no commit — operational).

### CLAUDE.md optimized (`24065ef`)
Fixed stale facts (version→`APP_VERSION` 3.67, app.py `~2,500`→2,785, gunicorn `8000`→**5000**,
Docker-Compose deploy instead of the abandoned systemd/native-Caddy), flagged `backup_tennis_db.sh`
as dead, replaced the drifted line-number index with **greppable symbol/route anchors**, and added
the backup sidecar, public `/rangliste`, WR-07 server-side winner recompute, and the two-box
same-hostname gotcha.

### Branch state (end of session)
- **`docker` merged → `main`** twice (clean fast-forwards, pushed). Verified **fully in sync**:
  `main` = `docker` = `origin/main` = `origin/docker` = **`24065ef`**; divergence `0 0`; no unique
  commits on either side.
- (This checkpoint edit is a later local change — commit/push to carry it forward; will then sit 1
  commit ahead of `main` until the next merge.)

### Notes / next
- **Box identity gotcha:** BOTH RPis report OS hostname `stechertennis`. Disambiguate by
  IP/domain/port — TEST=.213/nechvatal/10443, PROD=.180/tc-breakpoint-rangliste/10445. Always
  verify before deploying.
- Legacy **`backup_tennis_db.sh` is superseded** (targeted the abandoned native path + host
  `sqlite3`/`zip`). Not deleted. TEST box has local uncommitted edits to it + `check_db.sh`.
- Not yet observed: a *scheduled* top-of-hour run (next 19:00 UTC) — startup run + loop proven;
  watch `docker compose logs backup` after the hour to confirm cadence.
- Optional future: off-box DR (`rclone`/`rsync` of `daily/` to the other RPi or cloud).

## Current Session (2026-06-26) — Mobile-first layout, completed-challenges restyle, abbreviated tiebreaks, result-entry UX

Two UI rounds (v3.65), abbreviated tiebreaks (v3.66), result-entry UX rework (v3.67). **v3.67 live on TEST** (nechvatal).

### Result-entry UX rework (admin) — v3.67
- **Problem (many user complaints):** the score confirmation only fired on **blur** — typing a valid result
  did nothing visible; users had to click another field before the confirm prompt appeared.
- **Fix (client/template-only, `admin.html`; server `_parse_set_score`/WR-07 untouched):**
  - Validate live on every `input` (no focus change). New `evaluateForm()` is the single client source of
    truth, replacing `validateMatchResult`; removed the `blur` handler + `confirmed-value` gating.
  - Inline per-set errors: red border + `role="alert"`/`aria-live` message naming the set + expected
    formats — but only once a value is a *complete* score shape (so "6:" mid-typing isn't flagged early).
    Incomplete states show neutral amber guidance ("enter set 1 & 2", "1:1 — enter set 3").
  - Submit button enables the instant the result is valid, with a live green preview; **one** summary
    confirmation dialog on submit ("X gewinnt: 6:0 6:0 — jetzt absenden?") replaces the per-set blur modals.
  - A11y: `role=alert`/`aria-live`, `aria-invalid`, `aria-describedby`, `inputmode="numeric"`, `autocomplete=off`.
- **Verified live (chrome-devtools, real `input` events, no blur):** `6:0`→info; `8:6`→instant red error +
  format hint + red border; `6:`→reverts to neutral; `6:0`→submit enabled + green preview; winner mismatch→
  instant error; submit→confirm dialog with correct summary (cancelled, no DB write).
- Build/deploy: arm64 app image `:v3.67` + `:latest`, manifest `sha256:0dfca982…`; deployed to nechvatal,
  app Healthy, digest matches, startup log `version: 3.67`, `/login` → 200.

### `/rangliste` footer
- Removed the `Anmelden` (`<a href="/login">`) link; footer now reads "Tennis-Rangliste · Nur-Lese-Ansicht".

### Mobile-first pyramid (public `/rangliste`)
- The public pyramid clipped on phones (fixed-width boxes overflowed; rows 8–9 cut off both edges, portrait **and** landscape).
- A first attempt (container-relative `min()` width + non-square boxes) fit width-wise but rendered tall rectangles — user rejected it.
- **Final fix: mirror `index.html`'s pyramid CSS verbatim** so the public view matches the app at every breakpoint — square boxes stepping 100px → 90px (≤1200) → `calc((100vw-40px)/10-5px)` cap 65px (≤900, 3D off) → **32px (≤480)** → **`8vh` (phone landscape, max-height ≤500)**; ported the matching legend/entry font tweaks too.
- Verified with real mobile emulation (DPR 2.6, touch): 412px portrait → 32px boxes, `scrollW≈clientW` (no overflow); 915×412 landscape → `8vh` boxes, `scrollW==clientW`; 1280 desktop unchanged.
- **Gotcha:** chrome-devtools `resize_page` floors the CSS viewport at ~690px (devtools panel reserves width), so `≤480` never fires that way — use `emulate` (device viewport) for true phone testing.

### Completed-challenges list — clearer layout (both `/rangliste` and `/index`)
- Old: cramped `names · result · date` `space-between` row that wrapped awkwardly on mobile.
- New: **stacked entry** — bold matchup line (muted, smaller "gegen"), colored result+score line (green = challenger won / red = opponent won), muted date line, light divider between entries.
- Identical CSS/JS in both templates. Verified live on `/rangliste` (412px); `/index` shares the exact classes/markup but is login-gated, so not screenshotted.

### Local dev fixes (NOT committed — git-ignored / local-only)
- `.env`: the stacked prod block's `FLASK_DEBUG=false` (dotenv last-wins) won whenever the shell didn't export it → `SESSION_COOKIE_SECURE=True` over plain HTTP → no session cookie → **"CSRF session token is missing"** on local login. Set local `.env:71` `FLASK_DEBUG=false→true`. Prod box has its own clean `.env` (unaffected).
- Swapped local `tennis.db` to a copy of `db_backup_2026-06-25T19-12-09.db` (39 players); original backup untouched; previous DB kept as `tennis.db.prev-36players`.

### Committed this session
- `templates/public_ranking.html`, `templates/index.html`, `app.py` (version) + this checkpoint. Bumped **3.64 → 3.65**.

### Build + deploy (TEST)
- **arm64-only app-image build** (`docker buildx --platform linux/arm64 ... --push`, multiarch builder) — skipped the slow Caddy/multi-arch rebuild (Caddy unchanged; compose pins both to `:latest`). Pushed `:v3.65` + `:latest`, manifest `sha256:3fd74105…e0e427`.
- Deployed to nechvatal (`ssh stecher`, `docker compose pull app && up -d`): app **Healthy**, running image digest matches the pushed manifest, startup log `version: 3.65`.
- Verified on the Pi (`curl --resolve`, internal TLS): `/rangliste` → **200**; public API serves data with **no username/password/privilege leak**. (External LAN HTTPS not checkable — NAT hairpin.)

### Abbreviated tiebreak set scores (7:6 / 6:7) — v3.66
- **Sensitive logic** (winner is recomputed server-side from set scores, WR-07). Goal: accept `7:6`/`6:7`
  (tiebreak set, points omitted) in addition to the explicit `7:6(7:4)`.
- Rule for a `max==7` set: loser must have 5 or 6 games → valid `7:5` (diff 2) and `7:6` (diff 1); `7:7` and
  `7:4`-or-lower stay rejected.
- Two changes, kept in lockstep: `app.py:_parse_set_score` (`mx==7 and diff not in (1,2)`) and
  `admin.html:parseSetScore` (`maxGames===7 && (gameDiff<1 || gameDiff>2)`). The input sanitizer +
  `validScoreFormatRegex` already accepted bare `7:6` — only the winner logic rejected it.
- `tests/test_set_score.py`: 29-case truth-table regression. Server truth table 29/29; client parser
  (extracted from admin.html, run in node) matches server on all cases; `pytest` 11 passed.
- **Live E2E** (chrome-devtools, local app, real DB copy): logged in **THofer** (player) → `/admin` →
  challenge #149 Thomas Hofer→Erik Werner → entered `7:6` `7:6` through the real UI (winner select →
  per-set confirmation modals → submit). Server accepted; stored `score_details="7:6 7:6"`; re-ranked
  **Thomas Hofer 7→2, Erik Werner 2→3**. Logged in **MNechvatal** (superadmin) → `/index` shows it in
  the new stacked layout alongside an explicit-form entry `7:6(7:4) 7:6(8:6)`.
- **⚠️ The live test mutated the local `tennis.db`** (challenge #149 resolved, ranks shifted). Pre-test
  backup at `tennis.db.pretest-tiebreak` — restore with the app stopped if you want the untouched state.

### Build + deploy (TEST) — v3.66
- arm64-only app build pushed `:v3.66` + `:latest`, manifest `sha256:15c71e56…ea21d5a`.
- Deployed to nechvatal: app **Healthy**, running digest matches the push, startup log `version: 3.66`,
  `/rangliste` → **200**.

### Next
- Verify on a real phone via the TEST URL (`https://nechvatal.duckdns.org:10443`): mobile pyramid
  (portrait + landscape), completed-challenges layout, and a `7:6 7:6` result entry.
- Deploy to PROD (tc-breakpoint) when ready; IN-04 default superadmin password; deferred REVIEW findings.

## Current Session (2026-06-25) — Public read-only ranking page + v3.64

### Feature: public, unauthenticated, read-only ranking (`/rangliste`)
Implemented the "strongest" viewer-access option from the planning discussion: a public page
anyone can open with **no login, no credentials, no session** — nothing to leak, infinitely
concurrent, structurally read-only.
- `app.py`: two **GET-only** routes — `/rangliste` (renders `templates/public_ranking.html`,
  `X-Robots-Tag: noindex`) and `/api/public/ranking` (minimized JSON, `Cache-Control: public,
  max-age=10`, served from the existing 10s `get_realtime_data_cached()` so N viewers cause ≤1 DB
  read per cache window).
- Strict field whitelist (`_PUBLIC_PLAYER_FIELDS` / `_PUBLIC_CHALLENGE_FIELDS`) — the payload can
  **never** carry `username`, `password_hash`, or `privilege_level` (the authenticated `SELECT *`
  → `serialize_player` path leaks those; deliberately not reused).
- `templates/public_ranking.html`: self-contained read-only page (pyramid + collapsible status
  cards, 20s polling). No `<form>`, no CSRF, no Socket.IO, no write controls. Render logic adapted
  from index.html with all write/interactive parts stripped.
- **No DB writes** — purely additive read routes, no schema change, existing data untouched.
- Decision: this replaces the mandated shared-login "Zuseher" viewer account (that separate plan
  was NOT implemented — public page is more robust: no shared credential, no rate-limit lockout).

### Build + deploy
- Bumped 3.63 → **3.64** (`APP_VERSION` + index.html footer `25. Juni 2026`).
- Built multi-arch (amd64+arm64) via `build-and-push.sh`, pushed `:v3.64` + `:latest`. Deployed to
  the **nechvatal TEST box** (`ssh stecher`, `compose pull && up -d`) — both containers healthy,
  running `APP_VERSION="3.64"`.

### Tested live (chrome-devtools + curl) on nechvatal
- `/rangliste` loads unauthenticated (no session cookie); pyramid renders 39 players; cards
  active 8 / blocked 2 / unavailable 7 / completed 17.
- Feed: no `username`/`password_hash`/`privilege_level`; `POST /api/public/ranking` → **405**
  (no write path); headers `Cache-Control: public, max-age=10` + `X-Robots-Tag: noindex`.
- **Concurrency: 5 then 20 simultaneous viewers → 20/20 page 200 + 39 players, 16× parallel
  speedup (0.42s wall vs 6.78s serial), zero failures.**
- Verified locally first against a **COPY** of `db_backup_2026-06-25T19-12-09.db` (original untouched).

### Still open / next
- Deploy `/rangliste` to **PRODUCTION** (tc-breakpoint) when ready. Tip: app-image-only + arm64-only
  build is much faster than the full multi-arch (the Caddy image recompiles Caddy from source and
  hasn't changed).

## Current Session (2026-06-18, later) — NEW production server stand-up (club TC Breakpoint)

Stood up a **second production deployment** from scratch on a fresh **Raspberry Pi 5** for club *TC Breakpoint*.
**⚠️ This box is now production. The old `192.168.1.213` RPi is the TEST system.**

### Box identity & access
- **Prod:** `192.168.1.180`, OS hostname `stechertennis`, **FritzBox device label `tc-breakpoint`** (label ≠ hostname — see gotcha).
- SSH: `ssh -i ~/.ssh/stecher_tennis_key -o IdentitiesOnly=yes stecher@192.168.1.180 -p 10115` (key-only, passwordless sudo).
- RPi 5, Debian 12 bookworm, kernel 6.12, **NVMe SSD 917 GB**, 8 GB RAM, NTP synced (Europe/Vienna).

### Housekeeping (removed dead scaffolding)
- `~/stecher_tennis` was an **empty Python 3.11 venv** (no app code/DB) left from an abandoned native install → removed.
- Old DuckDNS cron pointed at `tc-breakpoint-forderung` and was **failing (502)** → removed. No Docker/Caddy/systemd app remnants.

### SSH hardening
- Set **`PermitRootLogin no`** in `/etc/ssh/sshd_config.d/50-keys-only.conf` (was `prohibit-password`), `sshd -t` OK, reloaded.
  Now: port 10115, password auth off, root login off, pubkey only.

### Local `.env` production-block fixes (untracked file, both test+prod blocks)
- `HTTPS_PORT` **10444 → 10445** (typo; must match FritzBox forward + CORS).
- `DUCKDNS_DOMAIN` **tc-breakpoint → tc-breakpoint-rangliste** (real domain; cert hostname must match).
- `SECRET_KEY` placeholder → **real 64-hex** (value lives only in `.env`, not here).
- `ACME_CA` staging → **production** (`acme-v02`).
- `.env` confirmed **git-ignored** (rule `.env` at `.gitignore:14`; never tracked/committed). Note: rule covers only `.env`, not `.env.*` variants.

### DuckDNS updater (reboot-safe)
- `~/duckdns/duck.sh` (perms 700), domain `tc-breakpoint-rangliste`, token in script (own DuckDNS acct, ≠ Nechvatal's).
- Manual run returned **`OK`** → token owns the subdomain. `*/5` cron installed; `cron` enabled at boot + crontab persisted on disk → survives reboot.
- `tc-breakpoint-rangliste.duckdns.org` resolves to **`178.190.41.149`** (the public IPv4).

### FritzBox (7590, FRITZ!OS 8.25 @ `192.168.1.254`, user wpl)
- Real **public IPv4 `178.190.41.149`** (not DS-Lite).
- Verified via UI (chrome-devtools): port share **`TC-BREAKPOINT` ext TCP 10445 → `192.168.1.180:10445`** (green/active). User reserved `.180` (static DHCP).
- Only 10445 forwarded — fine for **DNS-01** ACME (port 80 not needed). No conflict with test `.213` (which forwards 443/80/10556/10557).
- **Gotcha:** FritzBox labels are confusing — `.180`(prod) is labelled `tc-breakpoint`, `.213`(test) is labelled `stechertennis`. Routing is by IP; `.180` is correct.

### Docker install + deploy (v3.63)
- Installed Docker **29.5.3** + Compose **v5.1.4** via official `get.docker.com` script; service **enabled at boot**; `stecher` added to `docker` group (root-equiv).
- `git clone -b docker` → `~/stecher_tennis`; wrote **clean production-only `.env`** (KEY=VALUE only — did NOT copy the dual-block local `.env`, which would break parsing).
- `compose pull` (arm64) + `up -d`: app **healthy**, DB initialized + **seeded initial players**, both containers `restart=unless-stopped`.
- **Caddy obtained a real Let's Encrypt cert via DNS-01** for `tc-breakpoint-rangliste.duckdns.org` (issuer acme-v02, valid **Jun 18 → Sep 16 2026**). No staging volume to wipe (fresh box).
- Verified from Pi (`curl --resolve`): TLS verify=0, `302 → /login`, `/login` = **200**; `:80 → https` redirect works.
- Benign Caddy warning `unable to autosave config … read-only fs` — harmless (read_only container; cert storage on `caddy_data` volume).

### Reboot survival — VERIFIED (actually rebooted prod)
Rebooted `192.168.1.180` (boot_id changed) and confirmed the whole stack self-healed with **zero manual steps**:
- Docker service `active` (enabled at boot); both containers auto-restarted via `restart=unless-stopped` — app **healthy** within ~18s.
- HTTPS `/login` = **200**, `tls_verify=0` (trusted). **Caddy reused the cert from the `caddy_data` volume — no re-issuance** (no LE rate-limit hit).
- DuckDNS `*/5` cron still present; SSH back on 10115 (key-only, root off).
- Came back fully in ~30–40s. A power cut / unattended reboot recovers the site automatically.

### Post-deploy (same session) — DB restore + login handouts
- User **restored a newer DB** onto prod: now **41 accounts** = 39 players + 2 superadmins (M. Stecher `MStecher` r9, M. Nechvatal `MNechvatal` r19). Roster still carries the original Stecher-club names (restored from there, not a fresh TC-Breakpoint roster).
- Generated German login handouts from the **live** DB: `spieler.txt` (39 players) + `spieler_admins.txt` (2 admins). Login URL = `https://tc-breakpoint-rangliste.duckdns.org:10445`; usernames = initial(s)+surname; `/change_password` is admin-only (players can't self-change).
- Both handouts are **git-ignored** (`.gitignore: spieler*.txt`) — credentials never committed (passwords live only in the local files).

### ⏳ Still to confirm / do
- **External inbound test from cellular (Wi-Fi off):** `https://tc-breakpoint-rangliste.duckdns.org:10445` — only thing not verifiable from LAN (NAT-hairpin limitation). Everything up to the Pi is green.
- Consider changing the **default superadmin password** on the fresh DB (IN-04: default `DefaultPassword1!`).
- Optional: rename FritzBox `.180` device label to reduce confusion; add `@reboot` DuckDNS entry.

## Current Session (2026-06-18) — WR-04 DB-import fix + v3.63

### WR-04 fix: concurrency-safe DB import (testing-17062026.md "Round 3")
Tested the `/db_settings` DB import live (v3.62): worked but not "always-safe" — it used `shutil.copy2`
to overwrite the live DB (can corrupt concurrent readers mid-write), and only validated players/challenges.
Fixed in **v3.63**:
- `import_database` now uses the SQLite **backup API** (`src.backup(dst)`, same as export) — page-by-page under
  SQLite locking, safe with concurrent connections. Dropped the manual WAL-checkpoint/-wal/-shm cleanup and the
  now-unused `import shutil`.
- Validation additionally requires the `app_settings` table and `completed_challenges_view` (rejects
  structurally-incompatible `.db` up front instead of breaking at runtime).
Deployed v3.63, re-tested live: import fired with **25 parallel reads** → all returned 41 players, **zero
corruption**; data intact + writable after import; garbage/wrong-ext rejected (400); partial-schema DB rejected
(unit-verified). Production backed up (`~/tennis.preimport-v363.db`) and unchanged.
Note: web-UI import is the *safe* way to swap the DB — the app (appuser) writes it, so no root-owned/readonly trap.

## Current Session (2026-06-17, evening) — Production E2E test + WR-07 fix + v3.62

### Live E2E test of v3.61 (testing-17062026.md)
Ran a full browser+endpoint test against **production** (`nechvatal.duckdns.org`) as superadmin.
Server was free for testing for 3 days. **Backed up the live DB first** (41 players/119 challenges →
`~/tennis.pretest-backup-20260617.db` on RPi + in `tennis_data` volume), ran the destructive suite,
then **restored** — production data unchanged (verified Harbarth r1, 41 players, 36 matches).

**21 features PASS, 0 regressions.** Covered: login, pyramid, nav, Socket.IO, eligibility (all pyramid
tiers match source), challenge create→result→re-rank (with shift), opponent-wins + 7-day block (re-challenge
rejected), not_happened, availability toggle, new-player entry + name validation, admin UI, all DB-settings
ops, full DB reset, logout. **CR-02 confirmed fixed live** (duplicate names rejected on add + update).

**Issue found → WR-07 (confirmed live):** `/submit_result` did NOT cross-validate winner vs score. A direct
POST of `result=challenger_wins` with score `1:6 2:6` was accepted and promoted the loser (rank 42→13).
Client-side validation blocked it in-browser but was bypassable.
Also re-confirmed IN-04 (default password `DefaultPassword1!` returned to client) and that `/submit_result`
returns HTML not JSON. Not testable live: CR-01 (needs 10-day-expired deadline / TEST_DATE), WR-02 (needs a
player-level account).

### WR-07 fix (`515975b`, v3.62)
Added `_parse_set_score()` (server port of client `parseSetScore()`), recompute the winner from set scores
in `submit_result`, reject when it contradicts the claimed result — before any DB write. Added an early
result allowlist. Aufgabe/Disqualifikation/not_happened skip the score check. Bumped 3.61→3.62.
Verified: 9/9 tests pass; the exact bug case now rejects; valid 2/3-set + tie-break accept.

### v3.62 pushed, deployed + re-tested live (testing-17062026.md "Round 2")
Pushed `docker`, built multi-arch, deployed to RPi (`compose pull && up -d`, healthy, `APP_VERSION="3.62"`).
Re-ran the full suite against production (fresh backup `~/tennis.pretest-v362.db` → test → restore).
**WR-07 fix confirmed live**: `challenger_wins` + `1:6 2:6` now rejected (no write/no promotion); contradictory
`opponent_wins` and invalid formats rejected; valid results still accept + re-rank. 0 regressions; all Round-1
features re-pass. Production restored (41 players, Harbarth r1) and **writable**.

**⚠️ Operational gotcha found & fixed:** the earlier v3.61 restore left `/app/data/tennis.db` owned by `root`,
so the app (`appuser` uid 1000) could read but NOT write — production was effectively read-only between that
restore and the v3.62 round (challenge/result submits would have failed with "readonly database"). Hardened
containers (`cap_drop: ALL`) can't `chown` even as root; fixed via a one-off container `chown 1000:1000`.
**Lesson: any DB placed into the volume out-of-band MUST be chowned to uid 1000, then restart app.**

## Current Session (2026-06-17, later) — RPi 5 install guide

Authored `first-installation-RPi5.html` — a self-contained, mobile-first HTML checklist
for standing up a fresh **Raspberry Pi 5** production deployment from scratch (Docker-based).
No code changes to the app; documentation artifact only.

### What it covers (16 step cards, 0–14 + 1b)
- Fresh RPi OS install, SSH login, **SSH hardening (Step 1b)** (ed25519 keys,
  `PasswordAuthentication no`, custom port, with a lock-out safeguard).
- System update + NTP, static IP (FritzBox reservation or `nmtui`), Docker install.
- **DuckDNS**: subdomain + token, why DNS-01 ACME needs the token, `*/5` cron IP updater.
- **FritzBox**: two TCP port-forwards (ext 10443→int 443, ext 80→int 80); DS-Lite/public-IPv4
  warning; NAT-hairpin caveat.
- `git clone -b docker`, `.env` fill-in (all vars from `.env.example`), staging→production
  ACME switchover, function test, backup/auto-update/maintenance, troubleshooting table.

### Built from real repo config (not boilerplate)
Sourced from `prep_deploy.md`, `99_rpi.txt`, `.env.example`, `docker-compose.yml`, `Dockerfile`.

### Verified before handing off as a checklist
- GitHub repo `AINxtGenDev/stecher_tennis` → public (HTTP 200), clone needs no auth.
- Both GHCR images (`stecher-tennis-app`, `stecher-tennis-caddy`) → anonymous pull = 200.
- **Fixed a self-inflicted bug**: backup script originally called the `sqlite3` CLI, which is
  absent in the `python:3.12-slim` image. Rewrote to use Python's `sqlite3` backup API
  (guaranteed present, WAL-consistent).

Design: dark gradient hero, numbered step cards, color-coded callouts, scroll-progress bar,
copy-to-clipboard on every code block, mobile-first CSS with a 720px desktop enhancement.
Deliberately presents Docker as the sole production path (drops the legacy systemd/native-Caddy flow).

## Current Session (2026-06-17)

### Fixed 3 Critical findings + WR-03 (from REVIEW.md)

Acted on the review findings deferred last session. Each fix is an atomic commit;
all 9 tests pass (7 existing + 2 new smoke tests).

- **CR-02** (`11bb39c`) — Operator-precedence/casing bug in the UNIQUE-constraint
  check of `add_player` (`app.py:2064`) and `update_player` (`app.py:2159`). The
  `A or B and C` parse plus an uppercase `"UNIQUE"` literal searched in a
  `.lower()`'d string made branch A dead. Replaced both with the proven pattern
  from `newplayer_challenge`.
- **CR-03** (`1abf88e`) — In `resolve_expired_challenges`, moved `emit_data_update`
  outside the `with db:` block so it broadcasts only after the commit (was
  publishing uncommitted state).
- **CR-01** (`6ad71d8`) — `resolve_expired_challenges()` was dead code (never
  called). Added a throttled `@app.before_request` hook (runs at most once/min)
  that invokes it. Chose `before_request` over an eventlet background task because
  it runs identically under `python app.py` and gunicorn and doesn't depend on
  monkey-patching. Trade-off: cleanup only fires on traffic — fine for a 10-day rule.
- **WR-03** (`2dab8d0`) — Added `eventlet.monkey_patch()` at the very top of
  `app.py` (before `logging`, to avoid the lock deadlock). Restores dev/prod parity
  (gunicorn eventlet workers already patch). Added `tests/test_eventlet_patch.py`.
  Key correction to the review: `monkey_patch()` does NOT fix `sqlite3`/`bcrypt`
  blocking — those are C extensions; only `eventlet.tpool` would, which is a larger
  future change (deliberately out of scope).

### Version bump + deploy
- Bumped to **v3.61 • 17. Juni 2026** (`d89e03c`): `APP_VERSION` in app.py + footer in index.html.
- Built multi-arch (amd64 + arm64) via `build-and-push.sh`, pushed to GHCR:
  - app `:v3.61`/`:latest` → manifest `sha256:84aaec99…d3916`
  - caddy `:v3.61`/`:latest` → manifest `sha256:97391864…0724d`
  - GHCR_TOKEN was sourced from the stored docker `~/.docker/config.json` `ghcr.io` auth (no token in shell history).
- Deployed to RPi (`~/stecher_tennis`, `docker compose pull && up -d`). Verified:
  running container image digests match the pushed manifests, `APP_VERSION = "3.61"`,
  footer `Version: 3.61 • 17. Juni 2026`, app container `healthy`.
- External LAN HTTPS check (`:10443`) not confirmable — known NAT-hairpin router limitation.

### Merge + repo cleanup
- Merged `docker` → `main` (clean fast-forward; `main` was an exact ancestor, nothing lost).
  Both branches now at the same tip and pushed. ✓ Completes the "Merge docker → main" next step.
- Untracked 4 committed `tests/__pycache__/*.pyc` files (`50e60fd`) — they predated the
  `.gitignore __pycache__/` rule. Kept on disk, now ignored. Propagated to `main` too.
- Orphaned worktree commit `4da1a11` (tablet name-truncation fix) still NOT merged anywhere —
  lives only in worktree branch `worktree-agent-a2f0416f`. Revisit if that fix is still wanted.

### Still open (deferred)
- REVIEW.md: WR-01, WR-02, WR-05, WR-06 + 5 Info  (~~WR-07~~ v3.62, ~~WR-04~~ v3.63; IN-04 default passwords still open)
- REVIEW-TEMPLATES.md: all 13 findings (6 Warning, 7 Info)
- Deploy to second club (ts-breaking.duckdns.org)
- ~~Push + deploy v3.62 (WR-07 fix) + merge docker → main~~ done 2026-06-17/18

## Prior Session (2026-04-17)

### Code Review Pass (no code changes)
Spawned `gsd-code-reviewer` agents against `app.py` and all 5 templates. Produced two artifacts (not committed):

- `REVIEW.md` — app.py: 3 Critical, 7 Warning, 5 Info (15 total)
- `REVIEW-TEMPLATES.md` — templates: 0 Critical, 6 Warning, 7 Info (13 total)

### Top Findings (combined priority)

**Critical (app.py):**
1. **CR-01** — `resolve_expired_challenges()` at `app.py:743-814` is defined but **never called anywhere**. No `before_request` hook, no background task. Business rule "10-day auto-resolve" is silently broken; `is_new` flags on expired new-player challengers never clear.
2. **CR-02** — Operator-precedence bug in `add_player` (`app.py:2064-2069`) and `update_player` (`app.py:2159-2164`). `A or (B and C)` parsing plus an uppercase `"UNIQUE"` literal searched inside a `.lower()`'d haystack makes the first branch dead. Correct pattern already exists at `app.py:1868-1871` in `newplayer_challenge` — copy it.
3. **CR-03** — In `resolve_expired_challenges` (`app.py:766-805`), `emit_data_update` fires **inside** `with db:` despite a comment claiming "after commit". Broadcasts uncommitted state; if commit fails, clients hold rolled-back data.

**Warning (app.py):**
- WR-01 `emit_data_update("new_player_added")` labels player ID as `challenge_id` (`app.py:1839-1846`). `cursor.lastrowid` at that point refers to the player INSERT, not the challenge INSERT.
- WR-02 `@login_required` on Socket.IO handlers is ineffective (`app.py:2592-2604`). Follow the manual `current_user.is_authenticated` pattern from `handle_connect`.
- WR-03 No `eventlet.monkey_patch()` — `bcrypt`/`sqlite3`/`shutil.copy2` block the event loop.
- WR-04 `import_database` uses `shutil.copy2` on WAL-mode DB (`app.py:2480-2494`) — corruption risk; use sqlite3 backup API (already used for export).
- WR-05 `login_attempts` / `login_attempts_by_ip` dicts grow unbounded.
- WR-06 `reset_completed_challenges_display` uses `datetime.now()` instead of `get_current_time()` (`app.py:2378`) — breaks `TEST_DATE`.
- WR-07 `submit_result` has no result allowlist before DB writes.

**Warning (templates):**
- WR-01 Reflected XSS risk in `index.html:428, 443, 457` — three `.html(response.message)` calls inject server strings as raw HTML.
- WR-02 **Inconsistent nav privilege guards** — `admin.html:70-75` gates the admin link, but `index.html:243` and `db_settings.html:73` show it to everyone. (Already tracked as #14 in Remaining Items.)
- WR-03 `admin.html` Socket.IO `data_update` wipes in-progress result forms via `$challengesContainer.html(newContent)` (`admin.html:211`). Needs dirty-form guard.
- WR-04/05 `/eligible_opponents` XHR has no `.fail()` handler; array-vs-error shape detection is conflated (`index.html:429`).
- WR-06 `data-valid-play-dates='${JSON.stringify(...)}'` uses single-quoted attr with JSON; `JSON.stringify` doesn't escape `'` (latent; dates only today).

### What's Solid
- CSRF wiring (meta tag + `$.ajaxSetup beforeSend` + hidden form inputs) correct throughout
- `escapeHtml()` consistently applied for player-name insertions in index.html core
- Jinja auto-escaping covers all server-rendered output
- SRI hashes on all CDN resources
- `error.html` and `stecher_start.html` clean
- Recent fixes (parse_datetime helper, delta Socket.IO, SECRET_KEY enforcement, DB indexes) are solid

### No Code Changes This Session
User reviewed findings but deferred fixes. REVIEW.md and REVIEW-TEMPLATES.md remain untracked for a future fix session.

## Prior Session (2026-04-08)

### Container Hardening
Added security directives to both Docker containers in docker-compose.yml:
- `read_only: true` — immutable root filesystem (volumes remain writable)
- `security_opt: [no-new-privileges:true]` — prevents privilege escalation
- `cap_drop: [ALL]` — drops all Linux capabilities
- `tmpfs: /tmp` on app container for eventlet
- `cap_add: [NET_BIND_SERVICE]` on Caddy (required for binding ports 80/443)

### Issue: Caddy crash after cap_drop ALL
- `cap_drop: ALL` removed `NET_BIND_SERVICE` which Caddy needs → `exec /usr/bin/caddy: operation not permitted`
- Fixed by adding `cap_add: NET_BIND_SERVICE` back for Caddy only

## Prior Session (2026-04-06 evening → 2026-04-07)

### Code Review & Fixes
Performed full code review (security, quality, performance, frontend) and fixed the top 5 findings:

1. **SECRET_KEY required** — App crashes on startup if SECRET_KEY env var is missing instead of using insecure default
2. **Database indexes** — 4 new indexes on foreign keys and frequently filtered columns (schema.sql + auto-created in init_db for existing DBs)
3. **Delta Socket.IO updates** — `emit_data_update()` now queries only needed data sections per update type. Client `updateUI` handles partial payloads.
4. **parse_datetime() helper** — Replaced 26+ duplicated strptime patterns with single helper. Added `_get_field()` for safe access on sqlite3.Row objects.
5. **Silent except:pass eliminated** — Replaced with logged warnings

### Bugs Found & Fixed During Testing
- **sqlite3.Row .get() crash** — Fixed with `_get_field()` helper
- **Pyramid disappearing on availability toggle** — Fixed by requiring both `players` AND `active_challenges` for pyramid rebuild
- **FLASK_DEBUG=false breaks local dev** — Reverted .env to true (set false only on production Pi)

### Additional Fixes
- Removed leading dash from "gesperrt bis" text in blocked players list
- Bumped version to 3.60 • 7. April 2026
- Updated README: correct API routes, LOC counts, SECRET_KEY docs
- Removed obsolete report HTML files

### Comprehensive Testing (56 tests, 0 failures)
Full automated test via Chrome DevTools MCP — see `result.md` for details.

### Deployment
- Built multi-arch images (AMD64 + ARM64) via `build-and-push.sh`
- Pushed to GHCR: `ghcr.io/ainxtgendev/stecher-tennis-app:v3.60`
- Deployed to RPi: `docker compose pull && docker compose up -d`
- Both containers healthy: app + caddy

### Deployment
- `git pull` + `docker compose up -d` on RPi (compose-only change, no image rebuild needed)
- Verified: `docker inspect` confirms `ReadonlyRootfs: true`

## Commits (this session)
- `88f932a` fix: add NET_BIND_SERVICE cap for Caddy to bind ports 80/443
- `461f6df` security: harden Docker containers with read-only fs, no-new-privileges, cap-drop

## Prior Sessions
- 2026-04-06 evening → 2026-04-07: Code review, v3.60, delta updates, deploy
- 2026-04-06 afternoon: Bootstrap modals replacing native dialogs
- 2026-04-06 morning: Tablet pyramid display fix
- 2026-04-05: Result submission fix, Docker deployment setup

## RPi Deployment Notes
- **Production traffic** goes through Docker containers, NOT systemd service
- Deploy (image changes): `build-and-push.sh` → `ssh stecher 'cd ~/stecher_tennis && docker compose pull && docker compose up -d'`
- Deploy (compose-only changes): `ssh stecher 'cd ~/stecher_tennis && git pull && docker compose up -d'`
- Caddy runs as Docker container for HTTPS via DuckDNS DNS-01 ACME
- External HTTPS check from LAN fails (NAT hairpin issue — router limitation)

## Next Steps
- Merge docker → main
- Deploy to second club (ts-breaking.duckdns.org)

## Remaining Items
### Security
- C2: Hardcoded default passwords returned to client
- ~~#8 No container hardening in docker-compose.yml~~ ✓ Fixed 2026-04-08
- #9 Caddy receives all env vars including SECRET_KEY
- #14 Inconsistent nav bar privilege guard

### Performance
- P3-P8: Redundant queries, unused server-side pyramid, payload bloat (partially addressed by delta updates)

### Other
- Test coverage low (7 unit tests, no business logic coverage)
- RPi: clean up unused systemd service + native Caddy
