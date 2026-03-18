# Technology Stack

**Analysis Date:** 2026-03-18

## Languages

**Primary:**
- Python 3.12 - Backend application, main runtime

**Secondary:**
- HTML5 - Template engine (Jinja2 templating)
- JavaScript - Frontend DOM manipulation and Socket.IO client communication
- CSS - Styling with Bootstrap 5 and custom styles
- SQL - SQLite database queries and schema

## Runtime

**Environment:**
- Python 3.12 (specified in `environment.yml`)
- Runs on any OS supporting Python (Linux, macOS, Windows)

**Package Manager:**
- pip (Python package installer)
- Conda (for development environment management via `environment.yml`)
- Lockfile: `requirements.txt` for reproducible installs

## Frameworks

**Core:**
- Flask (web framework) - Located in `app.py`, provides HTTP routing and request handling
- Flask-SocketIO (real-time communication) - WebSocket implementation for live updates using Socket.IO protocol
- Jinja2 (template engine) - HTML template rendering, included with Flask

**Authentication & Security:**
- Flask-Login (user session management) - Handles login/logout and user loading
- Flask-WTF (CSRF protection) - Protects forms against Cross-Site Request Forgery attacks
- bcrypt (password hashing) - Secures user passwords with cryptographic hashing

**Testing:**
- pytest (test runner)
- Flask-Testing (Flask-specific testing utilities)
- coverage (code coverage reporting)

**Development/Debugging:**
- Flask-DebugToolbar (development debugging)
- black (code formatting)
- flake8 (code linting)
- watchdog (file monitoring for auto-reload)

**Build/Deployment:**
- gunicorn (production WSGI server)
- eventlet (async I/O library for Flask-SocketIO)
- greenlet (lightweight concurrency primitives)

## Key Dependencies

**Critical:**
- Flask (web framework backbone)
- Flask-SocketIO with eventlet (real-time bidirectional communication)
- bcrypt (password security - DO NOT REMOVE)
- Flask-Login (authentication system)
- Flask-WTF (CSRF protection - required for security)

**Infrastructure:**
- python-socketio & python-engineio (Socket.IO protocol implementation)
- simple-websocket (WebSocket support)
- Werkzeug (WSGI utilities, included with Flask)
- click (command-line interface utilities)
- itsdangerous (secure signing and session management)

**Data/Format:**
- Pillow (image processing - used for static assets)
- beautifulsoup4 (HTML parsing)
- pydantic (data validation)
- pyyaml (YAML parsing for environment.yml)

**External API Support (installed but may not be actively used):**
- google-generativeai (Google Gemini API client)
- openai (OpenAI API client)
- litellm (LLM abstraction layer)

**Analytics & Monitoring (installed but may not be actively used):**
- posthog (product analytics)
- mixpanel (analytics)

## Configuration

**Environment:**
- Loaded via `load_dotenv()` from `.env` file
- Key environment variables:
  - `SECRET_KEY` - Flask session encryption key
  - `FLASK_DEBUG` - Enable/disable debug mode (boolean: "true"/"false")
  - `FLASK_HOST` - Server bind address (default: "0.0.0.0")
  - `FLASK_PORT` - Server bind port (default: 5000)
  - `CORS_ALLOWED_ORIGINS` - Comma-separated allowed origins for CORS
  - `TEST_DATE` - Optional test date override

**Build:**
- `environment.yml` - Conda environment specification with all dev/test dependencies
- `requirements.txt` - Complete pip dependency list (includes dev and test packages)
- `prod-requirements.txt` - Minimal production dependency subset

## Database

**Technology:**
- SQLite 3 (file-based database, no server required)
- Database file: `tennis.db` in project root
- Schema: `schema.sql` (defines players and challenges tables)

**Connection:**
- sqlite3 Python standard library module
- No ORM used - direct SQL queries in `app.py`
- Row factory configured to return dictionaries for easy data access

## Platform Requirements

**Development:**
- Python 3.12
- Conda or pip for dependency management
- Standard POSIX shell (bash/zsh) for scripts
- ~500MB disk space for dependencies

**Production:**
- Python 3.12 runtime
- gunicorn WSGI server (production-grade)
- eventlet for async mode with Flask-SocketIO
- Web server/reverse proxy (nginx/Apache) recommended but not required
- SSL/TLS termination recommended (application uses ProxyFix middleware)

## Application Entry Point

**Location:** `app.py` (line 2557-2560)

**Startup Command:**
```python
if __name__ == "__main__":
    with app.app_context():
        init_db()
    logger.info("Starting Flask-SocketIO server with eventlet...")
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", 5000))
    socketio.run(app, host=host, port=port, debug=debug_mode, use_reloader=debug_mode)
```

**Production Startup:**
- Use gunicorn: `gunicorn --worker-class eventlet --workers 1 app:app`
- Configure via environment variables or gunicorn CLI flags

---

*Stack analysis: 2026-03-18*
