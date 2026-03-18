# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tennis ranking web application (v3.44) for a tennis club. Players view their ranking in a pyramid, challenge other players, and results automatically adjust rankings. German-language UI.

## Tech Stack

- **Backend**: Flask + Flask-SocketIO (eventlet async) + Flask-Login + Flask-WTF
- **Database**: SQLite 3 (WAL mode, foreign keys enabled)
- **Frontend**: Jinja2 templates, Bootstrap 5, jQuery, Socket.IO client
- **Auth**: bcrypt password hashing, three privilege levels (player/admin/superadmin)

## Commands

```bash
# Run development server (auto-initializes DB on first run)
python app.py

# Run tests
pytest

# Code formatting and linting
black app.py
flake8 app.py

# Database health check / backup
./check_db.sh
./backup_tennis_db.sh

# Production (single worker required for Socket.IO)
gunicorn --workers 1 --worker-class eventlet --bind 0.0.0.0:8000 app:app
```

## Architecture

The entire backend lives in a single `app.py` (~2,500 lines). There is no module separation — routes, business logic, database access, WebSocket handlers, and helpers are all in this file.

### Key Sections in app.py

- **Lines ~118-181**: Authentication (Flask-Login, rate limiting, privilege levels)
- **Lines ~228-256**: Data caching layer (10s TTL, thread-safe)
- **Lines ~259-352**: Data serialization (player/challenge objects → JSON)
- **Lines ~443-456**: Pyramid creation algorithm
- **Lines ~667-764**: Challenge eligibility rules (rank-distance based)
- **Lines ~765-791**: Ranking update logic on match result
- **Lines ~793-865**: Expired challenge resolution
- **Lines ~1024-1115**: Login/logout routes
- **Lines ~1116-1365**: Data API endpoints (`/api/realtime_data`, `/get_players`, `/eligible_opponents`)
- **Lines ~1365-2074**: Core action routes (challenge, result submission, availability toggle)
- **Lines ~2075-2322**: Admin routes (player CRUD, challenge management)
- **Lines ~2384-2492**: Superadmin routes (password reset, DB reset)
- **Lines ~2500-2544**: WebSocket event handlers

### Database

Schema defined in `schema.sql`. Three main structures:
- **players** table: rank, availability, blocking status, credentials
- **challenges** table: challenger/opponent, deadline (10 days), result, scheduled date
- **completed_challenges_view**: SQL VIEW joining challenges with player names

Initial data loaded from `initial_players.json` on DB reset.

### Real-time Updates

Socket.IO broadcasts to a `"tennis_updates"` room. All connected authenticated clients receive live data when rankings, challenges, or availability change.

### Challenge Business Rules

- Ranks 1-10: can challenge any higher-ranked player
- Ranks 11+: limited by rank distance (typically within 5 ranks)
- 7-day post-match block between same opponents
- Unavailable players cannot be challenged
- New (unranked) players enter by challenging someone in ranks 11-44

## Environment Configuration

Configured via `.env` file:
- `SECRET_KEY` — session encryption
- `CORS_ALLOWED_ORIGINS` — comma-separated trusted origins
- `FLASK_DEBUG` — enables debug mode
- `FLASK_HOST` / `FLASK_PORT` — bind address/port (defaults: 0.0.0.0 / 5000)
- `TEST_DATE` — override system time for testing (format: `YYYY-MM-DD-HH-MM-SS`)

## Deployment

Production target is a Raspberry Pi with systemd service and Caddy reverse proxy for HTTPS (via DuckDNS). See `documentation/99_rpi.txt` and README.md for full setup.
