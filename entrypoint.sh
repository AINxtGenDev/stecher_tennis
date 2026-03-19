#!/bin/bash
set -euo pipefail

# Initialize database if needed (safe — init_db() checks for existing tables)
echo "Initializing database at ${DB_PATH:-/app/data/tennis.db}..."
python -c "
from app import app, init_db
with app.app_context():
    init_db()
"

# exec replaces this shell with gunicorn so PID 1 is gunicorn (signal handling)
exec /venv/bin/gunicorn \
    --workers 1 \
    --worker-class eventlet \
    --bind 0.0.0.0:5000 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    app:app
