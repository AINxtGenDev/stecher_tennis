# -*- coding: utf-8 -*-
import re
import os
import shutil
import tempfile
from urllib.parse import urlparse
from dotenv import load_dotenv
import sqlite3
import json
import logging
import time
from datetime import datetime, timedelta, date
from flask import (
    Flask,
    g,
    request,
    jsonify,
    render_template,
    redirect,
    url_for,
    flash,
    send_file,
    after_this_request,
)
from flask_socketio import (
    SocketIO,
    emit,
    join_room,
    leave_room,
)
from threading import Lock

# --- NEW: Imports for Authentication and Security ---
import bcrypt
from functools import wraps
from flask_wtf.csrf import CSRFProtect
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user,
)

# --- MODIFIED: Import ProxyFix, it's still best practice ---
from werkzeug.middleware.proxy_fix import ProxyFix


load_dotenv()

# Determine run mode early to use it in configurations
debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() in ["true", "1"]

try:
    from flask.json import JSONEncoder as FlaskJSONEncoder

    class CustomJSONEncoder(FlaskJSONEncoder):
        def default(self, obj):
            if isinstance(obj, datetime):
                return obj.strftime("%Y-%m-%d %H:%M:%S")
            elif isinstance(obj, date):
                return obj.strftime("%Y-%m-%d")
            elif hasattr(obj, "__dict__"):
                return obj.__dict__
            return super().default(obj)

    CustomJSONProvider = None
except ImportError:
    from flask.json.provider import DefaultJSONProvider

    class CustomJSONProvider(DefaultJSONProvider):
        def default(self, obj):
            if isinstance(obj, datetime):
                return obj.strftime("%Y-%m-%d %H:%M:%S")
            elif isinstance(obj, date):
                return obj.strftime("%Y-%m-%d")
            elif hasattr(obj, "__dict__"):
                return obj.__dict__
            return super().default(obj)

    CustomJSONEncoder = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

APP_VERSION = "3.55"
logger.info(f"Starting Tennis App version: {APP_VERSION}")

app = Flask(__name__)

# --- MODIFIED: Keep ProxyFix for general proxy awareness (like correct IP logging) ---
# It's still good practice to have this so Flask knows it's behind a proxy.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)


app.secret_key = os.environ.get(
    "SECRET_KEY", "a-very-long-and-super-secret-key-for-dev"
)
if app.secret_key == "a-very-long-and-super-secret-key-for-dev":
    logger.warning(
        "SECURITY WARNING: Using default secret key. Set the SECRET_KEY environment variable for production."
    )

_db_path = os.environ.get("DB_PATH")
if _db_path:
    # Docker mode: use configured path, auto-create parent dirs
    _db_dir = os.path.dirname(_db_path)
    if _db_dir:
        os.makedirs(_db_dir, exist_ok=True)
    app.config["DATABASE"] = _db_path
else:
    # Non-Docker mode: keep current behavior (project root)
    app.config["DATABASE"] = os.path.join(app.root_path, "tennis.db")

# --- NEW/CRITICAL: Explicit configuration for CSRF protection behind a proxy ---
# This is the definitive fix for the "referrer does not match host" error.
prod_origins_str = os.environ.get("CORS_ALLOWED_ORIGINS")
if not debug_mode and prod_origins_str:
    # 1. Disable strict SSL referrer checking. This is often problematic with
    #    complex proxy setups, even when they are correctly configured.
    app.config["WTF_CSRF_SSL_STRICT"] = False

    # 2. Explicitly tell Flask-WTF which origins are trusted. This creates a
    #    whitelist and is the most secure way to solve the referrer issue.
    #    We derive it from the existing CORS_ALLOWED_ORIGINS env var.
    trusted_origins = [origin.strip() for origin in prod_origins_str.split(",")]
    app.config["WTF_CSRF_TRUSTED_ORIGINS"] = trusted_origins
    logger.info(f"Production CSRF trusted origins set to: {trusted_origins}")

# --- Upload size limit (50 MB) ---
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
app.config["SESSION_COOKIE_SECURE"] = not app.debug
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

if CustomJSONProvider:
    app.json = CustomJSONProvider(app)
else:
    app.json_encoder = CustomJSONEncoder

# --- NEW: CSRF Protection ---
csrf = CSRFProtect(app)


@app.route("/health")
@csrf.exempt
def health():
    return jsonify({"status": "ok"}), 200


# --- NEW: Flask-Login Configuration ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Bitte melde dich an, um auf diese Seite zuzugreifen."
login_manager.login_message_category = "warning"

# --- NEW: Rate Limiting for Login ---
login_attempts = {}
login_attempts_by_ip = {}
login_attempts_lock = Lock()
_db_import_lock = Lock()
MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_TIME = timedelta(minutes=5)


# --- NEW: User Model for Flask-Login ---
class User(UserMixin):
    def __init__(self, id, username, privilege_level):
        self.id = id
        self.username = username
        self.privilege_level = privilege_level


# --- NEW: User Loader for Flask-Login ---
@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    user_data = db.execute(
        "SELECT id, username, privilege_level FROM players WHERE id = ?", (user_id,)
    ).fetchone()
    if user_data:
        return User(
            id=user_data["id"],
            username=user_data["username"],
            privilege_level=user_data["privilege_level"],
        )
    return None


# --- NEW: Authorization Decorators ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.privilege_level not in [
            "admin",
            "superadmin",
        ]:
            flash("Du hast keine Berechtigung, auf diese Seite zuzugreifen.", "danger")
            return redirect(url_for("index"))
        return f(*args, **kwargs)

    return decorated_function


def superadmin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if (
            not current_user.is_authenticated
            or current_user.privilege_level != "superadmin"
        ):
            flash("Nur Super-Admins haben Zugriff auf diese Funktion.", "danger")
            return redirect(url_for("admin"))
        return f(*args, **kwargs)

    return decorated_function


# --- Socket.IO and CORS Configuration ---
allowed_origins = []

if prod_origins_str:
    allowed_origins.extend([origin.strip() for origin in prod_origins_str.split(",")])

if debug_mode:
    logger.info(
        "App is running in DEBUG mode. Adding local development origins to CORS."
    )
    dev_origins = ["http://127.0.0.1:5000", "http://localhost:5000"]
    for origin in dev_origins:
        if origin not in allowed_origins:
            allowed_origins.append(origin)

if not allowed_origins:
    logger.warning(
        "CORS_ALLOWED_ORIGINS not set and not in debug mode. Defaulting to '*'"
    )
    allowed_origins = "*"

socketio_kwargs = {
    "async_mode": "eventlet",
    "cors_allowed_origins": allowed_origins,
    "ping_timeout": 60,
    "ping_interval": 25,
    "logger": True,
    "engineio_logger": debug_mode,
}
if CustomJSONEncoder:
    socketio_kwargs["json"] = CustomJSONEncoder

socketio = SocketIO(app, **socketio_kwargs)

logger.info(
    f"CORS allowed origins configured for: {socketio.server_options.get('cors_allowed_origins')}"
)

if socketio.server_options.get("cors_allowed_origins") == "*":
    logger.warning(
        "SECURITY WARNING: CORS is configured to allow all origins. For production, set CORS_ALLOWED_ORIGINS in your .env file."
    )


class DataCache:
    def __init__(self, ttl=10):
        self.cache = {}
        self.ttl = ttl
        self.lock = Lock()

    def get(self, key):
        with self.lock:
            if key in self.cache:
                data, timestamp = self.cache[key]
                if time.time() - timestamp < self.ttl:
                    return data
                else:
                    del self.cache[key]
            return None

    def set(self, key, value):
        with self.lock:
            self.cache[key] = (value, time.time())

    def invalidate(self, key=None):
        with self.lock:
            if key:
                self.cache.pop(key, None)
            else:
                self.cache.clear()


data_cache = DataCache()


def serialize_player(player_row):
    player = dict(player_row)
    datetime_fields = [
        "unavailable_since",
        "block_challenger_until",
        "block_opponent_until",
    ]
    for field in datetime_fields:
        if player.get(field):
            if isinstance(player[field], str):
                try:
                    dt = datetime.strptime(
                        player[field].split(".")[0], "%Y-%m-%d %H:%M:%S"
                    )
                    player[f"{field}_formatted"] = dt.strftime("%Y-%m-%d %H:%M")
                    player[field] = dt.strftime("%Y-%m-%d %H:%M:%S")
                except (ValueError, TypeError):
                    player[f"{field}_formatted"] = "Invalid"
                    player[field] = None
            elif isinstance(player[field], datetime):
                player[f"{field}_formatted"] = player[field].strftime("%Y-%m-%d %H:%M")
                player[field] = player[field].strftime("%Y-%m-%d %H:%M:%S")
        else:
            player[f"{field}_formatted"] = None
    return player


def serialize_challenge(challenge_row):
    challenge = dict(challenge_row)
    if challenge.get("timestamp"):
        if isinstance(challenge["timestamp"], datetime):
            challenge["timestamp"] = challenge["timestamp"].strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        elif isinstance(challenge["timestamp"], str):
            challenge["timestamp"] = challenge["timestamp"].split(".")[0]
    if challenge.get("deadline"):
        if isinstance(challenge["deadline"], datetime):
            challenge["deadline_formatted"] = challenge["deadline"].strftime(
                "%Y-%m-%d %H:%M"
            )
            challenge["deadline"] = challenge["deadline"].strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(challenge["deadline"], str):
            try:
                dt = datetime.strptime(
                    challenge["deadline"].split(".")[0], "%Y-%m-%d %H:%M:%S"
                )
                challenge["deadline_formatted"] = dt.strftime("%Y-%m-%d %H:%M")
                challenge["deadline"] = dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                challenge["deadline_formatted"] = "N/A"
    if challenge.get("resolved_at"):
        if isinstance(challenge["resolved_at"], datetime):
            challenge["resolved_at_formatted"] = challenge["resolved_at"].strftime(
                "%Y-%m-%d %H:%M"
            )
            challenge["resolved_at"] = challenge["resolved_at"].strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        elif isinstance(challenge["resolved_at"], str):
            try:
                dt = datetime.strptime(
                    challenge["resolved_at"].split(".")[0], "%Y-%m-%d %H:%M:%S"
                )
                challenge["resolved_at_formatted"] = dt.strftime("%Y-%m-%d %H:%M")
                challenge["resolved_at"] = dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                challenge["resolved_at_formatted"] = "N/A"
    if challenge.get("scheduled_play_date"):
        if isinstance(challenge["scheduled_play_date"], datetime):
            challenge["scheduled_date"] = challenge["scheduled_play_date"].strftime(
                "%Y-%m-%d"
            )
            challenge["scheduled_time"] = challenge["scheduled_play_date"].strftime(
                "%H:%M"
            )
            challenge["scheduled_play_date"] = challenge[
                "scheduled_play_date"
            ].strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(challenge["scheduled_play_date"], str):
            try:
                dt = datetime.strptime(
                    challenge["scheduled_play_date"].split(".")[0], "%Y-%m-%d %H:%M:%S"
                )
                challenge["scheduled_date"] = dt.strftime("%Y-%m-%d")
                challenge["scheduled_time"] = dt.strftime("%H:%M")
                challenge["scheduled_play_date"] = dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                challenge["scheduled_date"] = None
                challenge["scheduled_time"] = None
    else:
        challenge["scheduled_date"] = None
        challenge["scheduled_time"] = None
    return challenge


def get_current_time():
    test_date_str = os.environ.get("TEST_DATE")
    if test_date_str:
        try:
            return datetime.strptime(test_date_str, "%Y-%m-%d-%H-%M-%S")
        except Exception as e:
            logger.exception(
                "Invalid TEST_DATE format: %s. Falling back to system time.",
                test_date_str,
            )
    return datetime.now()


def get_db():
    if "db" not in g:
        try:
            g.db = sqlite3.connect(
                app.config["DATABASE"], timeout=10, detect_types=sqlite3.PARSE_DECLTYPES
            )
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA journal_mode=WAL")
            g.db.execute("PRAGMA foreign_keys = ON")
        except sqlite3.Error as e:
            logger.exception("Database connection failed.")
            raise e
    return g.db


@app.teardown_appcontext
def close_db(error):
    db = g.pop("db", None)
    if db is not None:
        try:
            db.close()
        except sqlite3.Error:
            logger.exception("Failed to close the database connection.")


def init_db():
    db = get_db()
    try:
        cur = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='players';"
        )
        table_exists = cur.fetchone()
        if not table_exists:
            logger.info(
                "Database tables not found. Initializing schema and seeding data..."
            )
            schema_path = os.path.join(app.root_path, "schema.sql")
            with app.open_resource(schema_path) as f:
                db.executescript(f.read().decode("utf8"))

            json_path = os.path.join(app.root_path, "initial_players.json")
            with open(json_path, encoding="utf8") as json_file:
                data = json.load(json_file)
                for player in data["players"]:
                    plaintext_password = player["password"].encode("utf-8")
                    hashed_password = bcrypt.hashpw(
                        plaintext_password, bcrypt.gensalt()
                    )

                    db.execute(
                        """INSERT INTO players (id, name, username, password_hash, privilege_level, is_ranked_player, available, rank, is_new) 
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            player["id"],
                            player["name"],
                            player["username"],
                            hashed_password.decode("utf-8"),
                            player.get("privilege_level", "player"),
                            int(player["is_ranked_player"]),
                            int(player["is_available"]),
                            player["rank"],
                            0,
                        ),
                    )
            db.commit()
            logger.info("Database initialized and seeded with initial players.")
        else:
            logger.info("Database tables already exist. Skipping initialization.")
            db.execute("PRAGMA foreign_keys = ON")
        # Ensure app_settings table exists (for existing databases)
        db.execute(
            "CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT)"
        )
        db.commit()
    except Exception as e:
        logger.exception("Error during database initialization.")
        db.rollback()
        raise e


def create_pyramid(players):
    pyramid = []
    start = 0
    row_sizes = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    for size in row_sizes:
        row = []
        for i in range(size):
            if start < len(players):
                row.append(players[start])
            else:
                row.append(None)
            start += 1
        pyramid.append(row)
    return pyramid


def get_active_challenges():
    db = get_db()
    now_dt = get_current_time()
    now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    try:
        cur = db.execute(
            "SELECT c.*, p1.name as challenger_name, p2.name as opponent_name FROM challenges c "
            "JOIN players p1 ON c.challenger_id = p1.id "
            "JOIN players p2 ON c.opponent_id = p2.id "
            "WHERE c.resolved = 0 AND c.deadline > ?",
            (now_str,),
        )
        challenges_raw = cur.fetchall()
        challenges_processed = []
        for row in challenges_raw:
            challenge = dict(row)
            if isinstance(challenge.get("deadline"), str):
                try:
                    challenge["deadline"] = datetime.strptime(
                        challenge["deadline"].split(".")[0], "%Y-%m-%d %H:%M:%S"
                    )
                except (ValueError, TypeError):
                    challenge["deadline"] = None
            elif not isinstance(challenge.get("deadline"), datetime):
                challenge["deadline"] = None
            scheduled_play_date_val = challenge.get("scheduled_play_date")
            if isinstance(scheduled_play_date_val, str):
                try:
                    challenge["scheduled_play_date"] = datetime.strptime(
                        scheduled_play_date_val.split(".")[0], "%Y-%m-%d %H:%M:%S"
                    )
                except (ValueError, TypeError):
                    challenge["scheduled_play_date"] = None
            elif not isinstance(scheduled_play_date_val, datetime):
                challenge["scheduled_play_date"] = None
            if isinstance(challenge.get("timestamp"), str):
                try:
                    challenge["timestamp"] = datetime.strptime(
                        challenge["timestamp"].split(".")[0], "%Y-%m-%d %H:%M:%S"
                    )
                except (ValueError, TypeError):
                    challenge["timestamp"] = None
            elif not isinstance(challenge.get("timestamp"), datetime):
                challenge["timestamp"] = None
            challenge["valid_play_dates"] = []
            deadline_dt_obj = challenge.get("deadline")
            if isinstance(deadline_dt_obj, datetime):
                current_loop_date = now_dt.date()
                deadline_date = deadline_dt_obj.date()
                while current_loop_date <= deadline_date:
                    challenge["valid_play_dates"].append(current_loop_date.isoformat())
                    current_loop_date += timedelta(days=1)
            challenges_processed.append(challenge)
        return challenges_processed
    except sqlite3.Error:
        logger.exception("Error fetching active challenges.")
        return []


def get_completed_challenges(limit=50):
    db = get_db()
    try:
        hidden_before = None
        try:
            row = db.execute(
                "SELECT value FROM app_settings WHERE key = 'completed_challenges_hidden_before'"
            ).fetchone()
            if row:
                hidden_before = row["value"]
        except sqlite3.Error:
            pass
        if hidden_before:
            cur = db.execute(
                "SELECT * FROM completed_challenges_view WHERE resolved_at > ? LIMIT ?",
                (hidden_before, limit),
            )
        else:
            cur = db.execute(
                "SELECT * FROM completed_challenges_view LIMIT ?", (limit,)
            )
        challenges_raw = cur.fetchall()
        challenges_processed = []
        for row in challenges_raw:
            challenge = dict(row)
            if isinstance(challenge.get("resolved_at"), str):
                try:
                    challenge["resolved_at"] = datetime.strptime(
                        challenge["resolved_at"].split(".")[0], "%Y-%m-%d %H:%M:%S"
                    )
                except (ValueError, TypeError):
                    challenge["resolved_at"] = None
            elif not isinstance(challenge.get("resolved_at"), datetime):
                challenge["resolved_at"] = None
            if isinstance(challenge.get("timestamp"), str):
                try:
                    challenge["timestamp"] = datetime.strptime(
                        challenge["timestamp"].split(".")[0], "%Y-%m-%d %H:%M:%S"
                    )
                except (ValueError, TypeError):
                    challenge["timestamp"] = None
            elif not isinstance(challenge.get("timestamp"), datetime):
                challenge["timestamp"] = None
            if challenge.get("resolved_at"):
                challenge["resolved_at_fmt"] = challenge["resolved_at"].strftime(
                    "%Y-%m-%d %H:%M"
                )
            else:
                challenge["resolved_at_fmt"] = "N/A"
            challenges_processed.append(challenge)
        return challenges_processed
    except sqlite3.Error:
        logger.exception("Error fetching completed challenges.")
        return []


def get_active_challenge_ids():
    db = get_db()
    now_str = get_current_time().strftime("%Y-%m-%d %H:%M:%S")
    cur = db.execute(
        "SELECT challenger_id, opponent_id FROM challenges WHERE resolved = 0 AND deadline > ?",
        (now_str,),
    )
    active_ids = set()
    for row in cur.fetchall():
        active_ids.add(row["challenger_id"])
        active_ids.add(row["opponent_id"])
    return active_ids


def get_unavailable_players():
    db = get_db()
    try:
        cur = db.execute("SELECT * FROM players WHERE available = 0 ORDER BY rank ASC")
        players = cur.fetchall()
        players_with_formatted_dates = []
        for player in players:
            p = dict(player)
            if p.get("unavailable_since"):
                try:
                    unav_dt = p["unavailable_since"]
                    if isinstance(unav_dt, str):
                        unav_dt = datetime.strptime(
                            unav_dt.split(".")[0], "%Y-%m-%d %H:%M:%S"
                        )
                    elif not isinstance(unav_dt, datetime):
                        raise TypeError("unavailable_since is not a recognized type")
                    p["unavailable_since_fmt"] = unav_dt.strftime("%Y-%m-%d %H:%M")
                except (ValueError, TypeError, AttributeError) as e:
                    logger.warning(f"Could not format unavailable_since: {e}")
                    p["unavailable_since_fmt"] = "Ungültig"
            players_with_formatted_dates.append(p)
        return players_with_formatted_dates
    except sqlite3.Error:
        logger.exception("Error fetching unavailable players.")
        return []


def get_blocked_challenger_players():
    db = get_db()
    now = get_current_time().strftime("%Y-%m-%d %H:%M:%S")
    try:
        cur = db.execute(
            "SELECT * FROM players WHERE block_challenger_until IS NOT NULL AND block_challenger_until > ? ORDER BY rank ASC",
            (now,),
        )
        players = cur.fetchall()
        players_with_formatted_dates = []
        for player in players:
            p = dict(player)
            if p.get("block_challenger_until"):
                try:
                    block_dt = p["block_challenger_until"]
                    if isinstance(block_dt, str):
                        block_dt = datetime.strptime(
                            block_dt.split(".")[0], "%Y-%m-%d %H:%M:%S"
                        )
                    elif not isinstance(block_dt, datetime):
                        raise TypeError(
                            "block_challenger_until is not a recognized type"
                        )
                    p["block_challenger_until_fmt"] = block_dt.strftime(
                        "%Y-%m-%d %H:%M"
                    )
                except (ValueError, TypeError, AttributeError) as e:
                    logger.warning(f"Could not format block_challenger_until: {e}")
                    p["block_challenger_until_fmt"] = "Ungültig"
            players_with_formatted_dates.append(p)
        return players_with_formatted_dates
    except sqlite3.Error:
        logger.exception("Error fetching blocked challenger players.")
        return []


def get_blocked_opponent_players():
    db = get_db()
    now = get_current_time().strftime("%Y-%m-%d %H:%M:%S")
    try:
        cur = db.execute(
            "SELECT * FROM players WHERE block_opponent_until IS NOT NULL AND block_opponent_until > ? ORDER BY rank ASC",
            (now,),
        )
        players = cur.fetchall()
        players_with_formatted_dates = []
        for player in players:
            p = dict(player)
            if p.get("block_opponent_until"):
                try:
                    block_dt = p["block_opponent_until"]
                    if isinstance(block_dt, str):
                        block_dt = datetime.strptime(
                            block_dt.split(".")[0], "%Y-%m-%d %H:%M:%S"
                        )
                    elif not isinstance(block_dt, datetime):
                        raise TypeError("block_opponent_until is not a recognized type")
                    p["block_opponent_until_fmt"] = block_dt.strftime("%Y-%m-%d %H:%M")
                except (ValueError, TypeError, AttributeError) as e:
                    logger.warning(f"Could not format block_opponent_until: {e}")
                    p["block_opponent_until_fmt"] = "Ungültig"
            players_with_formatted_dates.append(p)
        return players_with_formatted_dates
    except sqlite3.Error:
        logger.exception("Error fetching blocked opponent players.")
        return []


def eligible_opponents_for(challenger):
    db = get_db()
    challenger_rank = challenger["rank"]
    now_dt = get_current_time()
    now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    active_ids = get_active_challenge_ids()
    if challenger_rank >= 11:
        is_challenger_blocked = False
        if challenger["block_challenger_until"]:
            try:
                block_dt = challenger["block_challenger_until"]
                if isinstance(block_dt, str):
                    block_dt = datetime.strptime(
                        block_dt.split(".")[0], "%Y-%m-%d %H:%M:%S"
                    )
                if isinstance(block_dt, datetime) and now_dt < block_dt:
                    is_challenger_blocked = True
            except (ValueError, TypeError, AttributeError) as e:
                logger.warning(
                    f"Could not parse block_challenger_until for eligibility check (challenger {challenger['id']}, value: '{challenger['block_challenger_until']}'): {e}"
                )
        if is_challenger_blocked:
            logger.info(
                f"Challenger {challenger['name']} (Rank {challenger_rank}) is blocked from challenging upwards until {challenger['block_challenger_until']}. No eligible opponents."
            )
            return []
    if challenger_rank <= 10:
        query = (
            "SELECT * FROM players WHERE rank < ? AND available = 1 "
            "AND id != ? "
            "AND (block_opponent_until IS NULL OR block_opponent_until <= ?) ORDER BY rank ASC"
        )
        parameters = (challenger_rank, challenger["id"], now_str)
        cur = db.execute(query, parameters)
        eligible = cur.fetchall()
        eligible = [p for p in eligible if p["id"] not in active_ids]
        return eligible
    if 11 <= challenger_rank <= 15:
        max_rank_diff = 4
    elif 16 <= challenger_rank <= 21:
        max_rank_diff = 5
    elif 22 <= challenger_rank <= 28:
        max_rank_diff = 6
    elif 29 <= challenger_rank <= 36:
        max_rank_diff = 7
    elif 37 <= challenger_rank <= 45:
        max_rank_diff = 8
    else:
        max_rank_diff = 0
    original_min_eligible_rank = max(1, challenger_rank - max_rank_diff)

    # Iteratively count unavailable players and extend the range
    # Each unavailable player in the current range allows extending by 1 position
    current_min_rank = original_min_eligible_rank
    previous_min_rank = None

    # Keep extending while we find new unavailable players in the extended range
    while current_min_rank != previous_min_rank and current_min_rank > 1:
        previous_min_rank = current_min_rank

        # Count unavailable players in the current range
        query_unavailable_count = (
            "SELECT COUNT(*) as unavailable_count FROM players "
            "WHERE rank >= ? AND rank < ? AND available = 0"
        )
        cur = db.execute(query_unavailable_count, (current_min_rank, challenger_rank))
        unavailable_count = cur.fetchone()["unavailable_count"]

        # Extend the range by the number of unavailable players
        # But still respect the original max_rank_diff limit for eligible opponents
        new_min_rank = max(1, original_min_eligible_rank - unavailable_count)

        # If we found new unavailable players in the extended range, continue
        if new_min_rank < current_min_rank:
            current_min_rank = new_min_rank
        else:
            break

    adjusted_min_eligible_rank = current_min_rank
    query = (
        "SELECT * FROM players WHERE rank >= ? AND rank < ? AND available = 1 "
        "AND id != ? "
        "AND (block_opponent_until IS NULL OR block_opponent_until <= ?) ORDER BY rank ASC"
    )
    parameters = (
        adjusted_min_eligible_rank,
        challenger_rank,
        challenger["id"],
        now_str,
    )
    cur = db.execute(query, parameters)
    eligible = cur.fetchall()
    # Filter out players who are currently in active challenges
    # They cannot be challenged while already in a challenge
    eligible = [p for p in eligible if p["id"] not in active_ids]
    return eligible


def rerank_players(db, allow_temporary_overflow=False):
    try:
        cur = db.execute(
            "SELECT id FROM players ORDER BY rank ASC, is_new DESC, id ASC"
        )
        players_to_rerank = cur.fetchall()
        new_rank_value = 1
        for row in players_to_rerank:
            db.execute(
                "UPDATE players SET rank = ? WHERE id = ?", (new_rank_value, row["id"])
            )
            new_rank_value += 1
        final_player_count = new_rank_value - 1
        if not allow_temporary_overflow and final_player_count > 45:
            logger.warning(
                f"Re-ranking resulted in {final_player_count} players. Deleting ranks > 45."
            )
            deleted_count = db.execute("DELETE FROM players WHERE rank > 45").rowcount
            logger.info(f"Deleted {deleted_count} players with rank > 45.")
        elif allow_temporary_overflow and final_player_count > 45:
            logger.info(
                f"Re-ranking resulted in {final_player_count} players. Temporary overflow allowed."
            )
    except sqlite3.Error as e:
        logger.exception("Error during player re-ranking.")
        raise e


def resolve_expired_challenges():
    """
    Finds and resolves any challenges where the deadline has passed.
    Sets their result to 'not_happened' and handles 'is_new' players.
    """
    db = get_db()
    now = get_current_time()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    try:
        # Find expired, unresolved challenges
        cur = db.execute(
            "SELECT id, challenger_id FROM challenges WHERE resolved = 0 AND deadline < ?",
            (now_str,),
        )
        expired_challenges = cur.fetchall()

        if not expired_challenges:
            return  # Nothing to do

        challenger_ids_of_expired_new_players = []
        challenge_ids_to_resolve = [c["id"] for c in expired_challenges]

        with db:  # Use a transaction
            # Check which of the challengers were new players
            for challenge in expired_challenges:
                challenger_cur = db.execute(
                    "SELECT is_new FROM players WHERE id = ?",
                    (challenge["challenger_id"],),
                )
                challenger = challenger_cur.fetchone()
                if challenger and challenger["is_new"] == 1:
                    challenger_ids_of_expired_new_players.append(
                        challenge["challenger_id"]
                    )

            # Bulk update challenges to 'not_happened'
            if challenge_ids_to_resolve:
                placeholders = ",".join("?" for _ in challenge_ids_to_resolve)
                db.execute(
                    f"UPDATE challenges SET resolved = 1, result = 'not_happened', resolved_at = ? WHERE id IN ({placeholders})",
                    (now, *challenge_ids_to_resolve),
                )

            # Bulk update new players so they are no longer 'is_new'
            if challenger_ids_of_expired_new_players:
                placeholders = ",".join(
                    "?" for _ in challenger_ids_of_expired_new_players
                )
                db.execute(
                    f"UPDATE players SET is_new = 0 WHERE id IN ({placeholders})",
                    (*challenger_ids_of_expired_new_players,),
                )

            logger.info(
                f"Automatically resolved {len(challenge_ids_to_resolve)} expired challenges as 'not_happened'."
            )
            # Invalidate cache and emit update *after* commit
            emit_data_update(
                "expired_challenges_resolved",
                {"resolved_ids": challenge_ids_to_resolve},
            )

    except sqlite3.Error as e:
        logger.exception(
            "Database error during automatic resolution of expired challenges."
        )
        # The 'with db:' block handles the rollback on error
    except Exception as e:
        logger.exception(
            "Unexpected error during automatic resolution of expired challenges."
        )


def get_realtime_data():
    db = get_db()
    now_dt = get_current_time()
    now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    try:
        cur = db.execute(
            """
            SELECT p.*,
                CASE
                  WHEN EXISTS (
                    SELECT 1 FROM challenges c
                    WHERE c.resolved = 0
                      AND c.deadline > ?
                      AND (c.challenger_id = p.id OR c.opponent_id = p.id)
                  ) THEN 1 ELSE 0
                END as in_challenge
            FROM players p
            WHERE p.is_ranked_player = 1
            ORDER BY rank ASC
        """,
            (now_str,),
        )
        players_raw = cur.fetchall()
        players = [serialize_player(p) for p in players_raw]
        for player in players:
            player["blocked_challenger"] = False
            player["blocked_opponent"] = False
            if player.get("block_challenger_until"):
                try:
                    block_dt = datetime.strptime(
                        player["block_challenger_until"], "%Y-%m-%d %H:%M:%S"
                    )
                    if now_dt < block_dt:
                        player["blocked_challenger"] = True
                except (ValueError, TypeError):
                    pass
            if player.get("block_opponent_until"):
                try:
                    block_dt = datetime.strptime(
                        player["block_opponent_until"], "%Y-%m-%d %H:%M:%S"
                    )
                    if now_dt < block_dt:
                        player["blocked_opponent"] = True
                except (ValueError, TypeError):
                    pass
        active_challenges = [serialize_challenge(c) for c in get_active_challenges()]
        completed_challenges = [
            serialize_challenge(c) for c in get_completed_challenges(limit=50)
        ]
        blocked_challenger_players = [
            serialize_player(p) for p in get_blocked_challenger_players()
        ]
        blocked_opponent_players = [
            serialize_player(p) for p in get_blocked_opponent_players()
        ]
        unavailable_players = [serialize_player(p) for p in get_unavailable_players()]
        return {
            "players": players,
            "active_challenges": active_challenges,
            "completed_challenges": completed_challenges,
            "blocked_challenger_players": blocked_challenger_players,
            "blocked_opponent_players": blocked_opponent_players,
            "unavailable_players": unavailable_players,
            "timestamp": now_dt.strftime("%Y-%m-%d %H:%M:%S"),
        }
    except Exception as e:
        logger.exception("Error getting realtime data")
        return None


def get_realtime_data_cached():
    cache_key = "realtime_data"
    cached_data = data_cache.get(cache_key)
    if cached_data:
        return cached_data
    fresh_data = get_realtime_data()
    if fresh_data:
        data_cache.set(cache_key, fresh_data)
        logger.debug("Generated and cached fresh realtime data")
    return fresh_data


def emit_to_room(event, data, room="tennis_updates"):
    try:
        socketio.emit(event, data, room=room)
        logger.debug(f"Emitted {event} to room {room}")
    except Exception as e:
        logger.error(f"Failed to emit {event} to room {room}: {e}")


def emit_data_update(update_type="general", specific_data=None):
    try:
        fresh_data = get_realtime_data()
        if fresh_data:
            data_cache.set("realtime_data", fresh_data)
            emit_to_room(
                "data_update",
                {
                    "type": update_type,
                    "data": fresh_data,
                    "specific": specific_data,
                    "timestamp": get_current_time().strftime("%Y-%m-%d %H:%M:%S"),
                },
            )
            logger.info(f"Emitted data_update (type: {update_type})")
        else:
            logger.error("Failed to get fresh realtime data for emission")
    except Exception as e:
        logger.exception(f"Error in emit_data_update: {e}")


# --- NEW: Helper function for username generation ---
def generate_username(full_name, db):
    """Generates a unique username based on the player's full name."""
    # Normalize name: "J.   Doe" -> "J. Doe"
    full_name = re.sub(r"\s+", " ", full_name).strip()
    parts = full_name.split(" ")

    if not parts:
        # Fallback for empty name
        base_username = "newplayer"
    elif len(parts) > 1:
        # "P. Krauskopf" -> initial="P", last_name="Krauskopf"
        # "Ch. Kramer" -> initial="Ch", last_name="Kramer"
        # "John Doe" -> initial="J", last_name="Doe"
        first_part = parts[0]
        if "." in first_part:
            initial = first_part.split(".")[0]
        else:
            initial = first_part[0]

        last_name = parts[-1]
        base_username = f"{initial}{last_name}"
    else:
        # Single name like "Cher"
        base_username = parts[0]

    # Sanitize to alphanumeric
    base_username = re.sub(r"[^a-zA-Z0-9]", "", base_username)
    if not base_username:  # If sanitization removed everything
        base_username = "player"

    # Ensure uniqueness
    username = base_username
    counter = 1
    while True:
        cur = db.execute("SELECT id FROM players WHERE username = ?", (username,))
        if not cur.fetchone():
            return username
        # If username exists, append a number and check again
        username = f"{base_username}{counter}"
        counter += 1


# --- ROUTES ---


@app.route("/")
def home():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # --- RATE LIMITING CHECK ---
        client_ip = request.remote_addr
        with login_attempts_lock:
            # Check IP-based rate limit
            ip_attempts, ip_last_time = login_attempts_by_ip.get(client_ip, (0, None))
            if ip_attempts >= MAX_LOGIN_ATTEMPTS and ip_last_time:
                time_since = datetime.now() - ip_last_time
                if time_since < LOGIN_LOCKOUT_TIME:
                    wait_time = LOGIN_LOCKOUT_TIME - time_since
                    wait_minutes = int(wait_time.total_seconds() / 60) + 1
                    flash(
                        f"Zu viele fehlgeschlagene Anmeldeversuche. Bitte warte {wait_minutes} Minute(n).",
                        "danger",
                    )
                    return redirect(url_for("login"))
                else:
                    login_attempts_by_ip.pop(client_ip, None)

            # Check username-based rate limit
            if username:
                attempts, last_attempt_time = login_attempts.get(username, (0, None))
                if attempts >= MAX_LOGIN_ATTEMPTS and last_attempt_time:
                    time_since_last_attempt = datetime.now() - last_attempt_time
                    if time_since_last_attempt < LOGIN_LOCKOUT_TIME:
                        wait_time = LOGIN_LOCKOUT_TIME - time_since_last_attempt
                        wait_minutes = int(wait_time.total_seconds() / 60) + 1
                        flash(
                            f"Zu viele fehlgeschlagene Anmeldeversuche. Bitte warte {wait_minutes} Minute(n).",
                            "danger",
                        )
                        return redirect(url_for("login"))
                    else:
                        login_attempts.pop(username, None)
        # --- END RATE LIMITING CHECK ---

        db = get_db()
        player_record = (
            db.execute(
                "SELECT * FROM players WHERE username = ?", (username,)
            ).fetchone()
            if username
            else None
        )

        login_successful = False
        if (
            player_record
            and password
            and bcrypt.checkpw(
                password.encode("utf-8"), player_record["password_hash"].encode("utf-8")
            )
        ):
            login_successful = True

        if login_successful:
            # --- SUCCESSFUL LOGIN ---
            with login_attempts_lock:
                login_attempts.pop(username, None)  # Clear attempts on success

            user = User(
                id=player_record["id"],
                username=player_record["username"],
                privilege_level=player_record["privilege_level"],
            )
            login_user(user)
            flash("Anmeldung erfolgreich!", "success")

            next_page = request.args.get("next")
            if next_page:
                parsed = urlparse(next_page)
                if not parsed.netloc and not parsed.scheme and next_page.startswith("/") and not next_page.startswith("//"):
                    return redirect(next_page)
                else:
                    return redirect(url_for("index"))

            # MODIFIED: All users are redirected to the index page.
            return redirect(url_for("index"))
        else:
            # --- FAILED LOGIN ---
            with login_attempts_lock:
                if username:
                    attempts, _ = login_attempts.get(username, (0, None))
                    login_attempts[username] = (attempts + 1, datetime.now())
                ip_attempts, _ = login_attempts_by_ip.get(client_ip, (0, None))
                login_attempts_by_ip[client_ip] = (ip_attempts + 1, datetime.now())

            flash("Ungültiger Benutzername oder Passwort.", "danger")
            return redirect(url_for("login"))

    return render_template("login_tennis.html")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Du wurdest erfolgreich abgemeldet.", "info")
    return redirect(url_for("login"))


@app.route("/api/realtime_data")
@login_required
def api_realtime_data():
    try:
        data = get_realtime_data_cached()
        if data:
            return jsonify({"success": True, "data": data})
        else:
            return jsonify({"success": False, "error": "Failed to get data"}), 500
    except Exception as e:
        logger.exception("Error in api_realtime_data")
        return jsonify({"success": False, "error": "Ein unerwarteter Fehler ist aufgetreten."}), 500


@app.route("/index")
@login_required
def index():
    try:
        all_data = get_realtime_data_cached()
        if not all_data:
            logger.error("Failed to retrieve data for index page rendering.")
            flash(
                "Konnte die Ranglistendaten nicht laden. Bitte versuche es später erneut.",
                "danger",
            )
            return (
                render_template(
                    "error.html", error_message="Daten konnten nicht geladen werden."
                ),
                500,
            )
        pyramid_data = create_pyramid(all_data.get("players", []))
        today_str = get_current_time().date().isoformat()
        return render_template(
            "index.html",
            pyramid=pyramid_data,
            players=all_data.get("players", []),
            active_challenges=all_data.get("active_challenges", []),
            completed_challenges=all_data.get("completed_challenges", []),
            blocked_challenger_players=all_data.get("blocked_challenger_players", []),
            blocked_opponent_players=all_data.get("blocked_opponent_players", []),
            unavailable_players=all_data.get("unavailable_players", []),
            today_date=today_str,
        )
    except Exception as e:
        logger.exception("Unexpected error on /index route.")
        flash("Ein unerwarteter Fehler ist aufgetreten.", "danger")
        return render_template("error.html", error_message="Unerwarteter Fehler"), 500


@app.route("/admin")
@login_required
def admin():
    db = get_db()
    try:
        now_str = get_current_time().strftime("%Y-%m-%d %H:%M:%S")
        cur = db.execute(
            "SELECT c.*, p1.name as challenger_name, p2.name as opponent_name FROM challenges c "
            "JOIN players p1 ON c.challenger_id = p1.id "
            "JOIN players p2 ON c.opponent_id = p2.id "
            "WHERE c.resolved = 0 AND c.deadline > ? ORDER BY c.deadline ASC",
            (now_str,),
        )
        challenges_raw = cur.fetchall()
        challenges_processed = []
        for row in challenges_raw:
            challenge = dict(row)
            if isinstance(challenge.get("deadline"), str):
                try:
                    challenge["deadline"] = datetime.strptime(
                        challenge["deadline"].split(".")[0], "%Y-%m-%d %H:%M:%S"
                    )
                except (ValueError, TypeError):
                    challenge["deadline"] = None
            elif not isinstance(challenge.get("deadline"), datetime):
                challenge["deadline"] = None
            challenges_processed.append(challenge)
        return render_template("admin.html", challenges=challenges_processed)
    except sqlite3.Error as e:
        logger.exception("Database error on /admin route.")
        flash(
            "Ein Datenbankfehler ist aufgetreten beim Laden der Admin-Seite.", "danger"
        )
        return redirect(url_for("index"))
    except Exception as e:
        logger.exception("Unexpected error on /admin route.")
        flash("Ein unerwarteter Fehler ist aufgetreten.", "danger")
        return redirect(url_for("index"))


@app.route("/get_players")
@login_required
def get_players():
    db = get_db()
    try:
        cur = db.execute("SELECT * FROM players ORDER BY rank ASC")
        players = cur.fetchall()
        active_ids = get_active_challenge_ids()
        current_time = get_current_time()
        players_list = []
        for p_row in players:
            p = dict(p_row)
            block_challenger = False
            block_opponent = False
            block_challenger_until_str = None
            block_opponent_until_str = None
            unavailable_since_str = None
            if p.get("block_challenger_until"):
                try:
                    block_until = p["block_challenger_until"]
                    if isinstance(block_until, str):
                        block_until = datetime.strptime(
                            block_until.split(".")[0], "%Y-%m-%d %H:%M:%S"
                        )
                    if isinstance(block_until, datetime) and current_time < block_until:
                        block_challenger = True
                        block_challenger_until_str = block_until.strftime(
                            "%Y-%m-%d %H:%M"
                        )
                except (ValueError, TypeError, AttributeError):
                    pass
            if p.get("block_opponent_until"):
                try:
                    block_until = p["block_opponent_until"]
                    if isinstance(block_until, str):
                        block_until = datetime.strptime(
                            block_until.split(".")[0], "%Y-%m-%d %H:%M:%S"
                        )
                    if isinstance(block_until, datetime) and current_time < block_until:
                        block_opponent = True
                        block_opponent_until_str = block_until.strftime(
                            "%Y-%m-%d %H:%M"
                        )
                except (ValueError, TypeError, AttributeError):
                    pass
            if p.get("unavailable_since"):
                try:
                    unav_dt = p["unavailable_since"]
                    if isinstance(unav_dt, str):
                        unav_dt = datetime.strptime(
                            unav_dt.split(".")[0], "%Y-%m-%d %H:%M:%S"
                        )
                    elif not isinstance(unav_dt, datetime):
                        raise TypeError("unavailable_since is not datetime")
                    unavailable_since_str = unav_dt.strftime("%Y-%m-%d %H:%M")
                except (ValueError, TypeError, AttributeError):
                    unavailable_since_str = "Ungültig"
            in_challenge = p["id"] in active_ids
            players_list.append(
                {
                    "id": p["id"],
                    "name": p["name"],
                    "username": p["username"],
                    "rank": p["rank"],
                    "available": bool(p["available"]),
                    "unavailable_since": unavailable_since_str,
                    "unavailability_reason": p.get("unavailability_reason"),
                    "block_challenger": block_challenger,
                    "block_opponent": block_opponent,
                    "block_challenger_until": block_challenger_until_str,
                    "block_opponent_until": block_opponent_until_str,
                    "block_challenger_until_fmt": block_challenger_until_str,
                    "block_opponent_until_fmt": block_opponent_until_str,
                    "in_challenge": in_challenge,
                    "is_new": bool(p["is_new"]),
                }
            )
        return jsonify(players_list)
    except sqlite3.Error as e:
        logger.exception("Database error on /get_players route.")
        return jsonify({"error": "Database error"}), 500


@app.route("/eligible_opponents", methods=["POST"])
@login_required
def eligible_opponents():
    challenger_id = request.form.get("challenger_id")
    if not challenger_id:
        return jsonify({"error": "Missing challenger_id"}), 400
    db = get_db()
    try:
        cur = db.execute("SELECT * FROM players WHERE id = ?", (challenger_id,))
        challenger = cur.fetchone()
        if not challenger:
            return jsonify({"error": "Challenger not found."}), 404
        if not challenger["available"]:
            return jsonify({"error": "Challenger is not available."}), 400
        now_dt = get_current_time()
        is_generally_blocked_as_challenger = False
        block_until_fmt = None
        if challenger["block_challenger_until"]:
            try:
                block_dt = challenger["block_challenger_until"]
                if isinstance(block_dt, str):
                    block_dt = datetime.strptime(
                        block_dt.split(".")[0], "%Y-%m-%d %H:%M:%S"
                    )
                if isinstance(block_dt, datetime) and now_dt < block_dt:
                    is_generally_blocked_as_challenger = True
                    block_until_fmt = block_dt.strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError, AttributeError):
                logger.warning(
                    f"Could not parse block_challenger_until for eligibility check: {challenger['block_challenger_until']}"
                )
        opponents = eligible_opponents_for(challenger)
        if (
            challenger["rank"] >= 11
            and is_generally_blocked_as_challenger
            and not opponents
        ):
            return (
                jsonify(
                    {
                        "error": f"{challenger['name']} (Rang {challenger['rank']}) ist bis {block_until_fmt} gesperrt und kann keine Aufstiegsspiele bestreiten."
                    }
                ),
                400,
            )
        elif (
            is_generally_blocked_as_challenger
            and not opponents
            and challenger["rank"] <= 10
        ):
            return (
                jsonify(
                    {
                        "error": f"{challenger['name']} ist bis {block_until_fmt} gesperrt."
                    }
                ),
                400,
            )
        opponents_list = [
            {
                "id": opp["id"],
                "name": opp["name"],
                "rank": opp["rank"],
                "available": bool(opp["available"]),
            }
            for opp in opponents
        ]
        return jsonify(opponents_list)
    except sqlite3.Error as e:
        logger.exception("Database error fetching eligible opponents.")
        return jsonify({"error": "Database error"}), 500
    except Exception as e:
        logger.exception("Unexpected error fetching eligible opponents.")
        return jsonify({"error": "Ein unerwarteter Fehler ist aufgetreten."}), 500


@app.route("/challenge", methods=["POST"])
@login_required
def challenge():
    challenger_id = request.form.get("challenger")
    opponent_id = request.form.get("opponent")
    if not challenger_id or not opponent_id:
        return jsonify({"error": "Both challenger and opponent must be selected."}), 400
    if str(current_user.id) != str(challenger_id) and current_user.privilege_level not in ("admin", "superadmin"):
        return jsonify({"error": "Nicht autorisiert."}), 403
    db = get_db()
    try:
        cur = db.execute("SELECT * FROM players WHERE id = ?", (challenger_id,))
        challenger = cur.fetchone()
        cur = db.execute("SELECT * FROM players WHERE id = ?", (opponent_id,))
        opponent = cur.fetchone()
        if not challenger or not opponent:
            return jsonify({"error": "Invalid player selection."}), 400
        if challenger_id == opponent_id:
            return jsonify({"error": "Cannot challenge yourself."}), 400
        now_dt = get_current_time()
        if not challenger["available"]:
            return jsonify({"error": f"{challenger['name']} is not available."}), 400
        challenger_blocked_general = False
        challenger_block_fmt = None
        if challenger["block_challenger_until"]:
            try:
                block_dt = challenger["block_challenger_until"]
                if isinstance(block_dt, str):
                    block_dt = datetime.strptime(
                        block_dt.split(".")[0], "%Y-%m-%d %H:%M:%S"
                    )
                if isinstance(block_dt, datetime) and now_dt < block_dt:
                    challenger_blocked_general = True
                    challenger_block_fmt = block_dt.strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError, AttributeError):
                pass
        if challenger_blocked_general:
            return (
                jsonify(
                    {
                        "error": f"{challenger['name']} is blocked from challenging until {challenger_block_fmt}."
                    }
                ),
                400,
            )
        if not opponent["available"]:
            return jsonify({"error": f"{opponent['name']} is not available."}), 400
        opponent_blocked = False
        opponent_block_fmt = None
        if opponent["block_opponent_until"]:
            try:
                block_dt = opponent["block_opponent_until"]
                if isinstance(block_dt, str):
                    block_dt = datetime.strptime(
                        block_dt.split(".")[0], "%Y-%m-%d %H:%M:%S"
                    )
                if isinstance(block_dt, datetime) and now_dt < block_dt:
                    opponent_blocked = True
                    opponent_block_fmt = block_dt.strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError, AttributeError):
                pass
        if opponent_blocked:
            return (
                jsonify(
                    {
                        "error": f"{opponent['name']} is blocked from being challenged until {opponent_block_fmt}."
                    }
                ),
                400,
            )
        active_ids = get_active_challenge_ids()
        if challenger["id"] in active_ids:
            return (
                jsonify(
                    {
                        "error": f"{challenger['name']} is already in an active challenge."
                    }
                ),
                400,
            )
        if opponent["id"] in active_ids:
            return (
                jsonify(
                    {"error": f"{opponent['name']} is already in an active challenge."}
                ),
                400,
            )
        eligible_opponents_list = eligible_opponents_for(challenger)
        if opponent["id"] not in [p["id"] for p in eligible_opponents_list]:
            if challenger["rank"] >= 11 and challenger_blocked_general:
                return (
                    jsonify(
                        {
                            "error": f"{challenger['name']} (Rang {challenger['rank']}) ist bis {challenger_block_fmt} gesperrt und kann keine Aufstiegsspiele bestreiten. {opponent['name']} ist kein gültiger Gegner."
                        }
                    ),
                    400,
                )
            return (
                jsonify(
                    {
                        "error": f"{opponent['name']} is not an eligible opponent for {challenger['name']}."
                    }
                ),
                400,
            )
        timestamp = get_current_time()
        deadline = timestamp + timedelta(days=10)
        cursor = db.execute(
            "INSERT INTO challenges (challenger_id, opponent_id, timestamp, deadline, resolved, score_details) VALUES (?, ?, ?, ?, ?, ?)",
            (challenger_id, opponent_id, timestamp, deadline, 0, None),
        )
        challenge_id = cursor.lastrowid
        db.commit()
        emit_data_update("challenge_created", {"challenge_id": challenge_id})
        message = f"Ich, {challenger['name']} (Rang {challenger['rank']}), fordere hiermit {opponent['name']} (Rang {opponent['rank']}) heraus."
        logger.info("Challenge created: %s vs %s", challenger["name"], opponent["name"])
        return jsonify(
            {
                "message": message,
                "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "challenge_id": challenge_id,
            }
        )
    except sqlite3.Error as e:
        db.rollback()
        logger.exception("Database error during challenge creation.")
        return jsonify({"error": "Database error during challenge creation."}), 500
    except Exception as e:
        logger.exception("Error during challenge validation or creation.")
        return jsonify({"error": "Ein unerwarteter Fehler ist aufgetreten."}), 500


@app.route("/toggle_availability", methods=["POST"])
@login_required
def toggle_availability():
    player_id = request.form.get("player_id")
    reason = request.form.get("reason")

    if not player_id:
        return jsonify({"success": False, "message": "No player_id provided."}), 400

    if str(current_user.id) != str(player_id) and current_user.privilege_level not in ("admin", "superadmin"):
        return jsonify({"success": False, "message": "Nicht autorisiert."}), 403

    if reason and len(reason) > 25:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Grund darf maximal 25 Zeichen lang sein.",
                }
            ),
            400,
        )

    db = get_db()
    try:
        cur = db.execute("SELECT * FROM players WHERE id = ?", (player_id,))
        player = cur.fetchone()
        if not player:
            return jsonify({"success": False, "message": "Player not found."}), 404
        active_ids = get_active_challenge_ids()
        if player["id"] in active_ids:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f"{player['name']} cannot change availability during an active challenge.",
                    }
                ),
                400,
            )
        new_availability = 0 if player["available"] == 1 else 1
        now_dt = get_current_time()
        with db:
            if new_availability == 0:
                db.execute(
                    "UPDATE players SET available = ?, unavailable_since = ?, unavailability_reason = ? WHERE id = ?",
                    (new_availability, now_dt, reason, player_id),
                )
                block_challenger_until_fmt = None
            else:
                block_challenger_until = now_dt + timedelta(days=3)
                db.execute(
                    "UPDATE players SET available = ?, unavailable_since = NULL, unavailability_reason = NULL, block_challenger_until = ? WHERE id = ?",
                    (new_availability, block_challenger_until, player_id),
                )
                block_challenger_until_fmt = block_challenger_until.strftime(
                    "%Y-%m-%d %H:%M"
                )
        logger.info(
            "Toggled availability for player %s (%s) to %s. Reason: %s",
            player_id,
            player["name"],
            new_availability,
            reason if new_availability == 0 else "N/A",
        )
        emit_data_update("availability_toggled", {"player_id": player_id})
        return jsonify(
            {
                "success": True,
                "new_availability": new_availability,
                "block_challenger_until": block_challenger_until_fmt,
            }
        )
    except sqlite3.Error as e:
        db.rollback()
        logger.exception("Error toggling availability.")
        return jsonify({"success": False, "message": "Database error."}), 500
    except Exception as e:
        logger.exception("Unexpected error toggling availability.")
        return (
            jsonify(
                {"success": False, "message": "Ein unerwarteter Fehler ist aufgetreten."}
            ),
            500,
        )


@app.route("/submit_result", methods=["POST"])
@login_required
def submit_result():
    challenge_id = request.form.get("challenge_id")
    result = request.form.get("result")
    special_result = request.form.get("special_result", "")
    set1_score = request.form.get("set1_score", "").strip()
    set2_score = request.form.get("set2_score", "").strip()
    set3_score = request.form.get("set3_score", "").strip()
    if not challenge_id or not result:
        flash("Invalid submission: Missing challenge ID or result type.", "danger")
        return redirect(url_for("admin"))

    db = get_db()
    try:
        cur = db.execute(
            "SELECT * FROM challenges WHERE id = ? AND resolved = 0", (challenge_id,)
        )
        challenge_record = cur.fetchone()
        if not challenge_record:
            flash("Challenge not found or already resolved.", "danger")
            return redirect(url_for("admin"))

        if current_user.privilege_level not in ("admin", "superadmin"):
            if str(current_user.id) not in (str(challenge_record["challenger_id"]), str(challenge_record["opponent_id"])):
                return jsonify({"success": False, "error": "Nicht autorisiert."}), 403

        score_details = None
        if result == "not_happened":
            score_details = "Nicht stattgefunden"
        elif special_result in ["Aufgabe", "Disqualifikation"]:
            score_details = special_result
        else:
            if set1_score and set2_score:
                if (
                    ":" in set1_score
                    and ":" in set2_score
                    and (not set3_score or ":" in set3_score)
                ):
                    sets = [set1_score, set2_score]
                    if set3_score:
                        sets.append(set3_score)
                    score_details = " ".join(sets)
                else:
                    flash(
                        "Invalid submission: Score format seems incorrect (e.g., use '6:4').",
                        "danger",
                    )
                    return redirect(url_for("admin"))
            elif result != "not_happened":
                flash(
                    "Invalid submission: Score for Set 1 and Set 2 is required unless 'Aufgabe' or 'Disqualifikation' is selected.",
                    "danger",
                )
                return redirect(url_for("admin"))
        if result in ["challenger_wins", "opponent_wins"] and not score_details:
            flash(
                "Invalid submission: Score details are missing or invalid for the selected result.",
                "danger",
            )
            return redirect(url_for("admin"))

        resolved_at = get_current_time()
        db.execute(
            "UPDATE challenges SET resolved = 1, result = ?, resolved_at = ?, score_details = ? WHERE id = ?",
            (result, resolved_at, score_details, challenge_id),
        )
        now = get_current_time()
        block_until = now + timedelta(days=7)
        challenger_id = challenge_record["challenger_id"]
        opponent_id = challenge_record["opponent_id"]
        cur = db.execute("SELECT * FROM players WHERE id = ?", (challenger_id,))
        challenger = cur.fetchone()
        cur = db.execute("SELECT * FROM players WHERE id = ?", (opponent_id,))
        opponent = cur.fetchone()
        if not challenger or not opponent:
            flash("Error: Player involved in challenge not found.", "danger")
            db.rollback()
            return redirect(url_for("admin"))
        db.execute(
            "UPDATE players SET block_challenger_until = NULL, block_opponent_until = NULL WHERE id IN (?, ?)",
            (challenger_id, opponent_id),
        )
        rank_changed = False
        if result == "challenger_wins":
            db.execute(
                "UPDATE players SET block_opponent_until = ? WHERE id = ?",
                (block_until, challenger_id),
            )
            db.execute(
                "UPDATE players SET block_challenger_until = ? WHERE id = ?",
                (block_until, opponent_id),
            )
            if challenger["rank"] > opponent["rank"]:
                rank_changed = True
                if challenger["is_new"] == 1:
                    new_rank = opponent["rank"]
                    db.execute(
                        "UPDATE players SET rank = rank + 1 WHERE rank >= ? AND rank <= 45 AND id != ?",
                        (new_rank, challenger_id),
                    )
                    db.execute(
                        "UPDATE players SET rank = ?, is_new = 0 WHERE id = ?",
                        (new_rank, challenger_id),
                    )
                    flash(
                        f"Rangliste aktualisiert: {challenger['name']} (Neu) gewinnt und steigt auf Rang {new_rank}.",
                        "success",
                    )
                else:
                    old_challenger_rank = challenger["rank"]
                    new_rank = opponent["rank"]
                    db.execute(
                        "UPDATE players SET rank = rank + 1 WHERE rank >= ? AND rank < ?",
                        (new_rank, old_challenger_rank),
                    )
                    db.execute(
                        "UPDATE players SET rank = ? WHERE id = ?",
                        (new_rank, challenger_id),
                    )
                    flash(
                        f"Rangliste aktualisiert: {challenger['name']} gewinnt und steigt auf Rang {new_rank}.",
                        "success",
                    )
            else:
                flash(f"{challenger['name']} gewinnt. Keine Rangänderung.", "info")
                if challenger["is_new"] == 1:
                    db.execute(
                        "UPDATE players SET is_new = 0 WHERE id = ?", (challenger_id,)
                    )
        elif result == "opponent_wins":
            db.execute(
                "UPDATE players SET block_opponent_until = ? WHERE id = ?",
                (block_until, opponent_id),
            )
            db.execute(
                "UPDATE players SET block_challenger_until = ? WHERE id = ?",
                (block_until, challenger_id),
            )
            if challenger["is_new"] == 1:
                deleted_count = db.execute(
                    "DELETE FROM players WHERE rank = 45"
                ).rowcount
                logger.info(
                    f"New player lost, removed player at rank 45 (count: {deleted_count}) to make space."
                )
                db.execute(
                    "UPDATE players SET is_new = 0 WHERE id = ?", (challenger_id,)
                )
                flash(
                    f"{opponent['name']} gewinnt. {challenger['name']} wird auf Rang 45 platziert.",
                    "info",
                )
            else:
                flash(f"Keine Rangänderung: {opponent['name']} gewinnt.", "info")
        elif result == "not_happened":
            if challenger["is_new"] == 1:
                db.execute(
                    "UPDATE players SET is_new = 0 WHERE id = ?", (challenger_id,)
                )
            flash(
                "Herausforderung als 'Nicht stattgefunden' markiert. Keine Rangänderung, keine neuen Sperren.",
                "info",
            )
        else:
            flash("Unbekanntes Ergebnis.", "danger")
            db.rollback()
            return redirect(url_for("admin"))
        with db:
            rerank_players(db, allow_temporary_overflow=False)
        emit_data_update(
            "result_submitted",
            {
                "challenge_id": challenge_id,
                "result": result,
                "rank_changed": rank_changed,
            },
        )
    except sqlite3.Error as e:
        db.rollback()
        logger.exception(f"Database error during challenge result submission: {e}")
        flash("Ein interner Fehler ist aufgetreten.", "danger")
    except Exception as e:
        db.rollback()
        logger.exception(f"Unexpected error during challenge result submission: {e}")
        flash("Ein unerwarteter Fehler ist aufgetreten.", "danger")
    return redirect(url_for("admin"))


@app.route("/newplayer_challenge", methods=["POST"])
@login_required
def newplayer_challenge():
    if current_user.privilege_level not in ("admin", "superadmin"):
        return jsonify({"error": "Nicht autorisiert."}), 403
    newplayer_name = request.form.get("newplayer_name", "").strip()
    opponent_id_str = request.form.get("opponent_id")
    if not newplayer_name or not opponent_id_str:
        return (
            jsonify({"error": "Neuer Spielername und Gegner müssen angegeben werden."}),
            400,
        )
    try:
        opponent_id = int(opponent_id_str)
    except ValueError:
        return jsonify({"error": "Ungültige Gegner-ID."}), 400
    letters_count = len(re.findall(r"[A-Za-z]", newplayer_name))
    has_digits = re.search(r"\d", newplayer_name)
    if letters_count < 5 or has_digits:
        return (
            jsonify(
                {
                    "error": "Neuer Spielername muss mindestens 5 Buchstaben enthalten und darf keine Zahlen beinhalten."
                }
            ),
            400,
        )
    db = get_db()
    try:
        cur_check_name = db.execute(
            "SELECT id FROM players WHERE lower(name) = lower(?)", (newplayer_name,)
        )
        if cur_check_name.fetchone():
            return (
                jsonify(
                    {"error": f"Spielername '{newplayer_name}' existiert bereits."}
                ),
                400,
            )
        cur_opponent_initial = db.execute(
            "SELECT * FROM players WHERE id = ?", (opponent_id,)
        )
        opponent = cur_opponent_initial.fetchone()
        if not opponent:
            return jsonify({"error": "Gegner nicht gefunden."}), 404
        original_opponent_name = opponent["name"]
        if not (11 <= opponent["rank"] <= 44):
            return (
                jsonify({"error": "Gegner muss initial zwischen Rang 11 und 44 sein."}),
                400,
            )
        if not opponent["available"]:
            return (
                jsonify(
                    {"error": f"Gegner {original_opponent_name} ist nicht verfügbar."}
                ),
                400,
            )
        now_dt = get_current_time()
        opponent_blocked = False
        opponent_block_fmt = None
        if opponent["block_opponent_until"]:
            try:
                block_dt = opponent["block_opponent_until"]
                if isinstance(block_dt, str):
                    block_dt = datetime.strptime(
                        block_dt.split(".")[0], "%Y-%m-%d %H:%M:%S"
                    )
                if isinstance(block_dt, datetime) and now_dt < block_dt:
                    opponent_blocked = True
                    opponent_block_fmt = block_dt.strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError, AttributeError):
                pass
        if opponent_blocked:
            return (
                jsonify(
                    {
                        "error": f"Gegner {original_opponent_name} ist bis {opponent_block_fmt} gesperrt."
                    }
                ),
                400,
            )
        active_ids = get_active_challenge_ids()
        if opponent["id"] in active_ids:
            return (
                jsonify(
                    {
                        "error": f"Gegner {original_opponent_name} ist bereits in einer aktiven Herausforderung."
                    }
                ),
                400,
            )
        timestamp = get_current_time()
        newplayer_id = None
        with db:
            # MODIFIED: Use new username generation and default password
            generated_username = generate_username(newplayer_name, db)
            default_password = "DefaultPassword1!".encode("utf-8")
            hashed_password = bcrypt.hashpw(default_password, bcrypt.gensalt()).decode(
                "utf-8"
            )

            cursor = db.execute(
                "INSERT INTO players (name, username, password_hash, available, rank, is_new, is_ranked_player) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (newplayer_name, generated_username, hashed_password, 1, 99, 1, 1),
            )
            newplayer_id = cursor.lastrowid
            if not newplayer_id:
                raise sqlite3.Error(
                    "Konnte die ID des neuen Spielers nicht abrufen nach dem Einfügen."
                )
            logger.info(
                f"New player '{newplayer_name}' inserted with temporary ID {newplayer_id} and rank 99."
            )
            rerank_players(db, allow_temporary_overflow=True)
            logger.info(
                f"Players re-ranked (allowing overflow). New player '{newplayer_name}' (ID: {newplayer_id}) now has a final rank."
            )
            cur_new_player_check = db.execute(
                "SELECT * FROM players WHERE id = ?", (newplayer_id,)
            )
            new_player_after_rerank = cur_new_player_check.fetchone()
            if not new_player_after_rerank:
                logger.error(
                    f"New player '{newplayer_name}' (ID: {newplayer_id}) was unexpectedly deleted during re-ranking. Rolling back."
                )
                raise sqlite3.Error(
                    f"Der neue Spieler '{newplayer_name}' konnte nicht korrekt der Rangliste hinzugefügt werden. Bitte versuche es erneut."
                )
            cur_opponent_after_rerank = db.execute(
                "SELECT * FROM players WHERE id = ?", (opponent_id,)
            )
            opponent_after_rerank = cur_opponent_after_rerank.fetchone()
            if not opponent_after_rerank:
                logger.error(
                    f"Opponent (ID: {opponent_id}, Name: {original_opponent_name}) was deleted during re-ranking (even with overflow allowed). This is unexpected. Rolling back."
                )
                raise sqlite3.Error(
                    f"Der ausgewählte Gegner ({original_opponent_name}) ist nach der Ranglistenanpassung nicht mehr verfügbar. Die Herausforderung kann nicht erstellt werden und der neue Spieler wurde NICHT hinzugefügt."
                )
            deadline = timestamp + timedelta(days=10)
            db.execute(
                "INSERT INTO challenges (challenger_id, opponent_id, timestamp, deadline, resolved, score_details) VALUES (?, ?, ?, ?, ?, ?)",
                (newplayer_id, opponent_id, timestamp, deadline, 0, None),
            )
            logger.info(
                f"Challenge created between new player {newplayer_id} ('{newplayer_name}') and opponent {opponent_id} ('{opponent_after_rerank['name']}')."
            )
            opponent_name_for_message = opponent_after_rerank["name"]
            opponent_new_rank = opponent_after_rerank["rank"]
            new_player_current_rank = new_player_after_rerank["rank"]
        emit_data_update(
            "new_player_added",
            {
                "player_id": newplayer_id,
                "player_name": newplayer_name,
                "challenge_id": cursor.lastrowid if "cursor" in locals() else None,
            },
        )
        message = f"{newplayer_name} (Neuer Spieler, Rang {new_player_current_rank}) fordert {opponent_name_for_message} (Rang {opponent_new_rank}) heraus. Frist: {deadline.strftime('%Y-%m-%d %H:%M')}"
        logger.info(
            "New player challenge successfully processed: %s (ID: %s, Rank: %s) vs %s (ID: %s, Rank: %s)",
            newplayer_name,
            newplayer_id,
            new_player_current_rank,
            opponent_name_for_message,
            opponent_id,
            opponent_new_rank,
        )
        # MODIFIED: Return username and password for modal display
        return jsonify(
            {
                "message": message,
                "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "new_player_username": generated_username,
                "new_player_password": "DefaultPassword1!",
            }
        )
    except sqlite3.IntegrityError as e:
        error_string = str(e).lower()
        is_name_unique_constraint_error = (
            "unique constraint failed" in error_string
            and "players.name" in error_string
        ) or ("not unique" in error_string and "players.name" in error_string)
        is_foreign_key_constraint_error = (
            "foreign key constraint failed" in error_string
        )
        if is_name_unique_constraint_error:
            logger.warning(
                f"IntegrityError (UNIQUE constraint on players.name) for new player '{newplayer_name}'. Error: {e}"
            )
            return (
                jsonify(
                    {"error": f"Spielername '{newplayer_name}' existiert bereits."}
                ),
                400,
            )
        elif is_foreign_key_constraint_error:
            logger.error(
                f"IntegrityError (FOREIGN KEY constraint failed) in newplayer_challenge. Challenger ID: {newplayer_id if newplayer_id else 'N/A'}, Opponent ID: {opponent_id_str}. Error: {e}"
            )
            return (
                jsonify(
                    {
                        "error": "Fehlerhafte Spieler-ID in der Herausforderung. Einer der Spieler existiert möglicherweise nicht mehr oder konnte nicht korrekt hinzugefügt werden."
                    }
                ),
                400,
            )
        else:
            logger.exception(
                f"Unhandled sqlite3.IntegrityError in newplayer_challenge. Error: {e}. newplayer_name='{newplayer_name}', opponent_id='{opponent_id_str}'"
            )
            return jsonify({"error": "Datenbank Integritätsfehler."}), 500
    except sqlite3.Error as e:
        logger.exception(
            f"SQLite error during new player challenge: '{str(e)}'. newplayer_name='{newplayer_name}', opponent_id='{opponent_id_str}'"
        )
        if "Der ausgewählte Gegner" in str(e) or "Der neue Spieler" in str(e):
            return jsonify({"error": str(e)}), 400
        return (
            jsonify(
                {
                    "error": "Datenbankfehler bei der Erstellung der neuen Spieler-Herausforderung."
                }
            ),
            500,
        )
    except Exception as e:
        logger.exception(
            f"Unexpected error during new player challenge: {e}. newplayer_name='{newplayer_name}', opponent_id='{opponent_id_str}'"
        )
        return jsonify({"error": "Ein unerwarteter Fehler ist aufgetreten."}), 500


@app.route("/update_scheduled_date", methods=["POST"])
@login_required
def update_scheduled_date():
    challenge_id_str = request.form.get("challenge_id")
    selected_date_str = request.form.get("selected_date")
    selected_time_str = request.form.get("selected_time")
    if not challenge_id_str:
        return jsonify({"success": False, "message": "Fehlende Challenge-ID."}), 400
    try:
        db = get_db()
        challenge_id = int(challenge_id_str)
        if current_user.privilege_level not in ("admin", "superadmin"):
            ch = db.execute(
                "SELECT challenger_id, opponent_id FROM challenges WHERE id = ?",
                (challenge_id,),
            ).fetchone()
            if not ch or str(current_user.id) not in (str(ch["challenger_id"]), str(ch["opponent_id"])):
                return jsonify({"success": False, "message": "Nicht autorisiert."}), 403
        scheduled_dt_obj = None
        if selected_date_str:
            time_str = selected_time_str if selected_time_str else "00:00"
            datetime_str = f"{selected_date_str} {time_str}"
            scheduled_dt_obj = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
            cur = db.execute(
                "SELECT deadline FROM challenges WHERE id = ? AND resolved = 0",
                (challenge_id,),
            )
            challenge_record = cur.fetchone()
            if not challenge_record:
                return (
                    jsonify(
                        {"success": False, "message": "Herausforderung nicht gefunden."}
                    ),
                    404,
                )
            deadline_dt = challenge_record["deadline"]
            if not isinstance(deadline_dt, datetime):
                deadline_dt = datetime.strptime(
                    str(deadline_dt).split(".")[0], "%Y-%m-%d %H:%M:%S"
                )
            if scheduled_dt_obj > deadline_dt:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "Spieldatum kann nicht nach der Frist liegen.",
                        }
                    ),
                    400,
                )
        db.execute(
            "UPDATE challenges SET scheduled_play_date = ? WHERE id = ?",
            (scheduled_dt_obj, challenge_id),
        )
        db.commit()
        emit_data_update("scheduled_date_updated", {"challenge_id": challenge_id})
        logger.info(
            f"Spieldatum für Herausforderung {challenge_id} auf {scheduled_dt_obj} gesetzt."
        )
        return jsonify(
            {"success": True, "message": "Spieldatum erfolgreich aktualisiert."}
        )
    except (ValueError, TypeError) as e:
        logger.warning(f"Invalid date/time format received: {e}")
        return (
            jsonify(
                {"success": False, "message": "Ungültiges Datums- oder Zeitformat."}
            ),
            400,
        )
    except sqlite3.Error as e:
        if "db" in locals() and db.in_transaction:
            db.rollback()
        logger.exception(
            f"DB-Fehler beim Aktualisieren des Spieldatums für Challenge {challenge_id_str}: {e}"
        )
        return jsonify({"success": False, "message": "Datenbankfehler."}), 500


# --- Admin Player Management Routes ---
@app.route("/add_player", methods=["POST"])
@admin_required
def add_player():
    data = request.get_json()
    if not data or "name" not in data or "rank" not in data:
        return jsonify({"success": False, "message": "Missing required fields."}), 400
    new_name = data["name"].strip()
    try:
        new_rank = int(data["rank"])
    except ValueError:
        return jsonify({"success": False, "message": "Invalid rank."}), 400
    if len(new_name) < 3:
        return (
            jsonify(
                {"success": False, "message": "Name must be at least 3 characters."}
            ),
            400,
        )
    if not (1 <= new_rank <= 45):
        return (
            jsonify({"success": False, "message": "Rank must be between 1 and 45."}),
            400,
        )
    db = get_db()
    try:
        cur_dup = db.execute(
            "SELECT id FROM players WHERE lower(name) = lower(?)", (new_name,)
        )
        if cur_dup.fetchone():
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f"Name '{new_name}' is already taken.",
                    }
                ),
                400,
            )
        with db:
            temp_username = new_name.replace(" ", "") + str(int(time.time()))
            temp_password = "PasswordForNewPlayer123!".encode("utf-8")
            temp_hashed_password = bcrypt.hashpw(
                temp_password, bcrypt.gensalt()
            ).decode("utf-8")

            db.execute(
                "INSERT INTO players (name, username, password_hash, available, rank, is_new, is_ranked_player) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (new_name, temp_username, temp_hashed_password, 1, new_rank, 0, 1),
            )
            logger.info(
                f"Admin added player '{new_name}' with initial rank {new_rank}."
            )
            rerank_players(db, allow_temporary_overflow=False)
            logger.info("Re-ranked players after admin add, enforcing 45 player limit.")
        emit_data_update("player_added", {"player_name": new_name})
        return jsonify(
            {
                "success": True,
                "message": f"Player '{new_name}' added successfully. Ranks recalculated.",
            }
        )
    except sqlite3.IntegrityError as e:
        if (
            "UNIQUE constraint failed: players.name" in str(e).lower()
            or "not unique" in str(e).lower()
            and "players.name" in str(e).lower()
        ):
            logger.warning(f"Admin add failed: Name '{new_name}' might be duplicate.")
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f"Name '{new_name}' might already exist.",
                    }
                ),
                400,
            )
        else:
            logger.exception(f"Admin add integrity error for player {new_name}: {e}")
            return (
                jsonify({"success": False, "message": "Database integrity error."}),
                500,
            )
    except sqlite3.Error as e:
        logger.exception(f"Error adding player {new_name} via admin: {e}")
        return jsonify({"success": False, "message": "Database error."}), 500
    except Exception as e:
        logger.exception(f"Unexpected error adding player {new_name} via admin: {e}")
        return (
            jsonify(
                {"success": False, "message": "Ein unerwarteter Fehler ist aufgetreten."}
            ),
            500,
        )


@app.route("/update_player", methods=["POST"])
@admin_required
def update_player():
    data = request.get_json()
    if not data or "id" not in data or "name" not in data or "rank" not in data:
        return jsonify({"success": False, "message": "Missing required fields."}), 400
    player_id = data["id"]
    new_name = data["name"].strip()
    try:
        new_rank = int(data["rank"])
    except ValueError:
        return jsonify({"success": False, "message": "Invalid rank."}), 400
    if new_name == "":
        return jsonify({"success": False, "message": "Name cannot be empty."}), 400
    if not (1 <= new_rank <= 45):
        return (
            jsonify({"success": False, "message": "Rank must be between 1 and 45."}),
            400,
        )
    db = get_db()
    try:
        cur = db.execute("SELECT rank, name FROM players WHERE id = ?", (player_id,))
        player = cur.fetchone()
        if not player:
            return jsonify({"success": False, "message": "Player not found."}), 404
        old_name = player["name"]
        if new_name.lower() != old_name.lower():
            cur_dup = db.execute(
                "SELECT id FROM players WHERE lower(name) = lower(?) AND id != ?",
                (new_name, player_id),
            )
            if cur_dup.fetchone():
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": f"Name '{new_name}' is already taken.",
                        }
                    ),
                    400,
                )
        with db:
            db.execute(
                "UPDATE players SET name = ?, rank = ? WHERE id = ?",
                (new_name, new_rank, player_id),
            )
            logger.info(
                f"Admin updated player {player_id}. Name: {new_name}, Rank attempt: {new_rank}. Preserved blocks."
            )
            rerank_players(db, allow_temporary_overflow=False)
            logger.info(
                "Re-ranked players after admin update, enforcing 45 player limit."
            )
        emit_data_update("player_details_updated", {"player_id": player_id})
        return jsonify(
            {
                "success": True,
                "message": "Player updated successfully. Ranks recalculated.",
            }
        )
    except sqlite3.IntegrityError as e:
        if (
            "UNIQUE constraint failed: players.name" in str(e).lower()
            or "not unique" in str(e).lower()
            and "players.name" in str(e).lower()
        ):
            logger.warning(
                f"Admin update failed: Name '{new_name}' might be duplicate."
            )
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f"Name '{new_name}' might already exist.",
                    }
                ),
                400,
            )
        else:
            logger.exception(
                f"Admin update integrity error for player {player_id}: {e}"
            )
            return (
                jsonify({"success": False, "message": "Database integrity error."}),
                500,
            )
    except sqlite3.Error as e:
        logger.exception(f"Error updating player {player_id} via admin: {e}")
        return jsonify({"success": False, "message": "Database error."}), 500
    except Exception as e:
        logger.exception(f"Unexpected error updating player {player_id} via admin: {e}")
        return (
            jsonify(
                {"success": False, "message": "Ein unerwarteter Fehler ist aufgetreten."}
            ),
            500,
        )


@app.route("/delete_player", methods=["POST"])
@admin_required
def delete_player():
    data = request.get_json()
    if not data or "id" not in data:
        return jsonify({"success": False, "message": "Missing player id."}), 400
    player_id = data["id"]
    db = get_db()
    try:
        cur = db.execute("SELECT name FROM players WHERE id = ?", (player_id,))
        player = cur.fetchone()
        if not player:
            return jsonify({"success": False, "message": "Player not found."}), 404
        player_name = player["name"]
        with db:
            player_deleted = db.execute(
                "DELETE FROM players WHERE id = ?", (player_id,)
            ).rowcount
            if player_deleted == 0:
                raise sqlite3.Error(
                    "Player could not be deleted after existence check."
                )
            logger.info(f"Admin deleted player {player_id} ({player_name}).")
            rerank_players(db, allow_temporary_overflow=False)
            logger.info(
                "Re-ranked players after admin delete, enforcing 45 player limit."
            )
        emit_data_update("player_deleted", {"player_name": player_name})
        return jsonify(
            {
                "success": True,
                "message": f"Player '{player_name}' deleted successfully. Ranks recalculated.",
            }
        )
    except sqlite3.Error as e:
        logger.exception(
            f"Error deleting player {player_id} ({player_name if 'player_name' in locals() else 'N/A'}): {e}"
        )
        return (
            jsonify({"success": False, "message": "Database error during deletion."}),
            500,
        )
    except Exception as e:
        logger.exception(f"Unexpected error deleting player {player_id}: {e}")
        return (
            jsonify(
                {"success": False, "message": "Ein unerwarteter Fehler ist aufgetreten."}
            ),
            500,
        )


@app.route("/set_player_block_status", methods=["POST"])
@admin_required
def set_player_block_status():
    data = request.get_json()
    if not data or "player_id" not in data or "block_type" not in data:
        return jsonify({"success": False, "message": "Missing required fields."}), 400
    player_id = data["player_id"]
    block_type = data["block_type"]
    if block_type not in ["none", "challenger", "opponent"]:
        return (
            jsonify({"success": False, "message": "Invalid block type specified."}),
            400,
        )
    db = get_db()
    try:
        cur = db.execute("SELECT id, name FROM players WHERE id = ?", (player_id,))
        player = cur.fetchone()
        if not player:
            return jsonify({"success": False, "message": "Player not found."}), 404
        player_name = player["name"]
        now = get_current_time()
        block_duration = timedelta(days=7)
        block_until = now + block_duration
        with db:
            if block_type == "none":
                db.execute(
                    "UPDATE players SET block_challenger_until = NULL, block_opponent_until = NULL WHERE id = ?",
                    (player_id,),
                )
                log_msg = f"Admin {current_user.username} cleared block status for player {player_id} ({player_name})."
            elif block_type == "challenger":
                db.execute(
                    "UPDATE players SET block_challenger_until = ?, block_opponent_until = NULL WHERE id = ?",
                    (block_until, player_id),
                )
                log_msg = f"Admin {current_user.username} set player {player_id} ({player_name}) as blocked challenger until {block_until}."
            elif block_type == "opponent":
                db.execute(
                    "UPDATE players SET block_opponent_until = ?, block_challenger_until = NULL WHERE id = ?",
                    (block_until, player_id),
                )
                log_msg = f"Admin {current_user.username} set player {player_id} ({player_name}) as blocked opponent until {block_until}."
        logger.info(log_msg)
        emit_data_update("block_status_updated", {"player_id": player_id})
        return jsonify(
            {"success": True, "message": f"Block status for '{player_name}' updated."}
        )
    except sqlite3.Error as e:
        logger.exception(f"Error setting block status for player {player_id}: {e}")
        return jsonify({"success": False, "message": "Database error."}), 500
    except Exception as e:
        logger.exception(
            f"Unexpected error setting block status for player {player_id}: {e}"
        )
        return (
            jsonify(
                {"success": False, "message": "Ein unerwarteter Fehler ist aufgetreten."}
            ),
            500,
        )


@app.route("/change_password", methods=["POST"])
@admin_required
def change_password():
    data = request.get_json()
    if not data or "player_id" not in data or "new_password" not in data:
        return jsonify({"success": False, "message": "Missing required fields."}), 400

    player_id = data["player_id"]
    new_password = data["new_password"]

    if len(new_password) < 8:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Password must be at least 8 characters long.",
                }
            ),
            400,
        )

    db = get_db()
    try:
        cur = db.execute("SELECT name FROM players WHERE id = ?", (player_id,))
        player = cur.fetchone()
        if not player:
            return jsonify({"success": False, "message": "Player not found."}), 404

        hashed_password = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())

        with db:
            db.execute(
                "UPDATE players SET password_hash = ? WHERE id = ?",
                (hashed_password.decode("utf-8"), player_id),
            )

        logger.info(
            f"Admin '{current_user.username}' successfully changed password for player ID {player_id} ({player['name']})."
        )
        return jsonify(
            {
                "success": True,
                "message": f"Password for {player['name']} has been updated.",
            }
        )

    except sqlite3.Error as e:
        logger.exception(
            f"Database error changing password for player {player_id}: {e}"
        )
        return jsonify({"success": False, "message": "Database error."}), 500
    except Exception as e:
        logger.exception(
            f"Unexpected error changing password for player {player_id}: {e}"
        )
        return (
            jsonify({"success": False, "message": "An unexpected error occurred."}),
            500,
        )


@app.route("/reset_completed_challenges_display", methods=["POST"])
@superadmin_required
def reset_completed_challenges_display():
    db = get_db()
    try:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.execute(
            "INSERT OR REPLACE INTO app_settings (key, value) VALUES ('completed_challenges_hidden_before', ?)",
            (now_str,),
        )
        db.commit()
        logger.info(
            f"Completed challenges display reset by superadmin {current_user.username} at {now_str}."
        )
        emit_data_update("challenges_display_reset")
        return jsonify(
            {
                "success": True,
                "message": "Durchgeführte Herausforderungen wurden zurückgesetzt.",
            }
        )
    except sqlite3.Error as e:
        logger.exception("Database error resetting completed challenges display.")
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Datenbankfehler.",
                }
            ),
            500,
        )


@app.route("/api/settings/db/export", methods=["GET"])
@superadmin_required
def export_database():
    db_path = app.config["DATABASE"]
    if not os.path.exists(db_path):
        return jsonify({"success": False, "message": "Datenbankdatei nicht gefunden."}), 404
    # Create a consistent snapshot using sqlite3 backup API
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(tmp_fd)
    try:
        src_conn = sqlite3.connect(db_path)
        dst_conn = sqlite3.connect(tmp_path)
        src_conn.backup(dst_conn)
        dst_conn.close()
        src_conn.close()
    except Exception as e:
        logger.exception("Failed to create DB snapshot for export.")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return jsonify({"success": False, "message": "Export fehlgeschlagen."}), 500

    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")

    @after_this_request
    def cleanup(response):
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
        return response

    return send_file(
        tmp_path,
        as_attachment=True,
        download_name=f"db_backup_{timestamp}.db",
        mimetype="application/octet-stream",
    )


@app.route("/api/settings/db/import", methods=["POST"])
@superadmin_required
def import_database():
    if "db_file" not in request.files:
        return jsonify({"success": False, "message": "Keine Datei hochgeladen."}), 400
    file = request.files["db_file"]
    if not file.filename or not file.filename.endswith(".db"):
        return jsonify({"success": False, "message": "Nur .db-Dateien sind erlaubt."}), 400

    db_path = app.config["DATABASE"]
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".db")
    try:
        os.close(tmp_fd)
        file.save(tmp_path)
        # Validate that the uploaded file is a valid SQLite database
        try:
            conn = sqlite3.connect(tmp_path)
            result = conn.execute("PRAGMA integrity_check").fetchone()
            if result[0] != "ok":
                conn.close()
                return jsonify({"success": False, "message": "Die Datei ist keine gültige SQLite-Datenbank."}), 400
            # Validate schema: ensure required tables and columns exist
            try:
                conn.execute("SELECT id, name, username, password_hash, rank, available, privilege_level FROM players LIMIT 1")
                conn.execute("SELECT id, challenger_id, opponent_id, timestamp, deadline, resolved, result FROM challenges LIMIT 1")
            except sqlite3.OperationalError:
                conn.close()
                return jsonify({"success": False, "message": "Die Datenbank hat nicht das erwartete Schema (players/challenges Tabellen fehlen oder sind unvollständig)."}), 400
            conn.close()
        except sqlite3.DatabaseError:
            return jsonify({"success": False, "message": "Die Datei ist keine gültige SQLite-Datenbank."}), 400

        # Close existing connection and replace with WAL checkpoint + lock
        with _db_import_lock:
            # Checkpoint WAL to ensure all data is in the main DB file
            try:
                live_conn = sqlite3.connect(db_path)
                live_conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                live_conn.close()
            except Exception:
                pass  # DB may not exist yet or not be in WAL mode
            close_db(None)
            shutil.copy2(tmp_path, db_path)
            # Remove stale WAL/SHM files
            for suffix in ("-wal", "-shm"):
                wal_path = db_path + suffix
                if os.path.exists(wal_path):
                    os.remove(wal_path)
        logger.info(f"Database imported by superadmin {current_user.username}")
        return jsonify({"success": True, "message": "Datenbank erfolgreich importiert. Seite wird neu geladen."})
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.route("/reset_database", methods=["POST"])
@superadmin_required
def reset_database():
    db = get_db()
    try:
        with db:
            logger.warning(
                f"Attempting database reset by superadmin {current_user.username}..."
            )
            db.execute("DROP VIEW IF EXISTS completed_challenges_view;")
            db.execute("DROP TABLE IF EXISTS challenges;")
            db.execute("DROP TABLE IF EXISTS players;")
            db.execute("DROP TABLE IF EXISTS app_settings;")
            logger.info("Existing tables and views dropped.")

            init_db()

        logger.info("Database reset successful.")
        emit_data_update("database_reset")
        return jsonify(
            {"success": True, "message": "Datenbank erfolgreich zurückgesetzt."}
        )
    except sqlite3.Error as e:
        logger.exception("Database error during reset.")
        return (
            jsonify(
                {"success": False, "message": "Datenbankfehler beim Zurücksetzen."}
            ),
            500,
        )
    except Exception as e:
        logger.exception("Unexpected error during database reset.")
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Unerwarteter Fehler beim Zurücksetzen.",
                }
            ),
            500,
        )


# --- Other Routes ---
@app.route("/db_settings")
@superadmin_required
def db_settings():
    return render_template("db_settings.html")


@app.route("/initial_players")
@superadmin_required
def initial_players():
    return render_template("initial_players.html")


# --- SocketIO Event Handlers ---
@socketio.on("connect")
def handle_connect():
    if not current_user.is_authenticated:
        logger.warning(
            f"Unauthenticated client tried to connect: {request.sid}. Disconnecting."
        )
        return False

    logger.info(
        f"Authenticated client connected: {current_user.username} ({request.sid})"
    )
    join_room("tennis_updates")
    try:
        data = get_realtime_data_cached()
        if data:
            emit("data_update", {"type": "initial_connection", "data": data})
    except Exception as e:
        logger.exception(f"Error sending initial data to {request.sid}: {e}")
    emit(
        "connection_ack",
        {
            "status": "connected",
            "server_time": get_current_time().strftime("%Y-%m-%d %H:%M:%S"),
        },
    )


@socketio.on("disconnect")
def handle_disconnect():
    logger.info(f"Client disconnected: {request.sid}")
    leave_room("tennis_updates")


@socketio.on("request_full_update")
@login_required
def handle_request_full_update():
    logger.info(f"Client {request.sid} requested a full data update.")
    data = get_realtime_data_cached()
    if data:
        emit("data_update", {"type": "full_update_requested", "data": data})


@socketio.on("ping")
@login_required
def handle_ping():
    emit("pong", {"timestamp": get_current_time().strftime("%Y-%m-%d %H:%M:%S")})


@socketio.on_error_default
def default_error_handler(e):
    logger.error(f"SocketIO Error: {e} from SID {request.sid}")


# --- Main Execution ---
if __name__ == "__main__":
    with app.app_context():
        init_db()
    logger.info("Starting Flask-SocketIO server with eventlet...")
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", 5000))
    socketio.run(app, host=host, port=port, debug=debug_mode, use_reloader=debug_mode)
