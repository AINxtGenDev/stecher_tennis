# -*- coding: utf-8 -*-
import re
import os
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from flask import Flask, g, request, jsonify, render_template, redirect, url_for, flash
from flask_socketio import SocketIO, emit  # Ensure Flask-SocketIO is installed

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["DATABASE"] = os.path.join(app.root_path, "tennis.db")
app.secret_key = (
    "your-secret-key"  # In production, load this from an environment variable
)

#######################################################
# Initialize SocketIO - use this for development only
# socketio = SocketIO(app, async_mode="threading")
# Initialize SocketIO - use this for production
#######################################################
socketio = SocketIO(app, async_mode="eventlet")


def get_current_time():
    """
    Returns the current datetime.
    If the environment variable TEST_DATE is set (in format YYYY-MM-DD-HH-MM-SS),
    it parses and returns that value. This enables testing by simulating a future/past date.
    """
    test_date_str = os.environ.get("TEST_DATE")
    if test_date_str:
        try:
            # Expected format: "2025-03-13-21-13-23"
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
            # Enable Foreign Key support
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
    """Initializes the database: Creates tables and loads initial data ONLY if tables don't exist."""
    db = get_db()
    try:
        # Check if the 'players' table already exists as an indicator of initialized DB
        cur = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='players';"
        )
        table_exists = cur.fetchone()

        if not table_exists:
            logger.info("Database tables not found. Initializing schema...")
            # --- Create Schema ---
            try:
                schema_path = os.path.join(app.root_path, "schema.sql")
                with app.open_resource(schema_path) as f:
                    # IMPORTANT: Execute script ONLY if tables don't exist
                    # The schema.sql still contains DROP IF EXISTS, which is fine here
                    # as it won't do anything if the tables are truly missing.
                    db.executescript(f.read().decode("utf8"))
                db.commit()  # Commit schema creation
                logger.info("Database schema initialized.")
            except Exception as e:
                logger.exception("Error initializing the database schema.")
                db.rollback()  # Rollback on schema error
                raise e  # Re-raise to prevent inconsistent state

            # --- Load Initial Data (only if schema was just created) ---
            # Check count again AFTER potentially creating the table
            cur_check = db.execute("SELECT COUNT(*) as count FROM players")
            count_after_init = cur_check.fetchone()["count"]
            logger.info("Players count after schema init: %s", count_after_init)

            if count_after_init == 0:
                try:
                    json_path = os.path.join(app.root_path, "initial_players.json")
                    with open(json_path, encoding="utf8") as json_file:
                        data = json.load(json_file)
                        for player in data["players"]:
                            try:
                                db.execute(
                                    "INSERT INTO players (id, name, available, rank, unavailable_since, is_new) VALUES (?, ?, ?, ?, ?, ?)",
                                    (
                                        player["id"],
                                        player["name"],
                                        int(player["is_available"]),
                                        player["rank"],
                                        None,
                                        0,
                                    ),
                                )
                            except sqlite3.IntegrityError:
                                logger.warning(
                                    f"Initial player name '{player['name']}' might already exist (should not happen on fresh init). Skipping."
                                )
                    db.commit()  # Commit initial data loading
                    logger.info("Loaded initial players from JSON.")
                except Exception as e:
                    logger.exception("Error loading initial players from JSON.")
                    db.rollback()  # Rollback initial data loading on error
                    # Don't raise here, allow app to continue but log the error
            else:
                logger.info(
                    "Initial players already exist or schema init failed to create table. Skipping initial data load."
                )

        else:
            logger.info(
                "Database tables already exist. Skipping schema initialization and initial data load."
            )
            # Ensure foreign keys are enabled on subsequent connections even if schema wasn't run now
            db.execute("PRAGMA foreign_keys = ON")

    except sqlite3.Error as e:
        logger.exception("SQLite error during init_db check/setup.")
    except Exception as e:
        logger.exception("Unexpected error during init_db.")


def create_pyramid(players):
    pyramid = []
    start = 0
    row_sizes = [1, 2, 3, 4, 5, 6, 7, 8]
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
    now = get_current_time().strftime("%Y-%m-%d %H:%M:%S")
    try:
        cur = db.execute(
            "SELECT c.*, p1.name as challenger_name, p2.name as opponent_name FROM challenges c "
            "JOIN players p1 ON c.challenger_id = p1.id "
            "JOIN players p2 ON c.opponent_id = p2.id "
            "WHERE c.resolved = 0 AND c.deadline > ?",
            (now,),
        )
        challenges_raw = cur.fetchall()
        challenges_processed = []
        for row in challenges_raw:
            challenge = dict(row)
            # Ensure deadline is datetime object
            if isinstance(challenge.get("deadline"), str):
                try:
                    deadline_str = challenge["deadline"].split(".")[0]
                    challenge["deadline"] = datetime.strptime(
                        deadline_str, "%Y-%m-%d %H:%M:%S"
                    )
                except (ValueError, TypeError):
                    challenge["deadline"] = None  # Handle parsing error
            elif not isinstance(challenge.get("deadline"), datetime):
                challenge["deadline"] = None  # Handle unexpected type

            # Ensure timestamp is datetime object (less critical for display, but good practice)
            if isinstance(challenge.get("timestamp"), str):
                try:
                    timestamp_str = challenge["timestamp"].split(".")[0]
                    challenge["timestamp"] = datetime.strptime(
                        timestamp_str, "%Y-%m-%d %H:%M:%S"
                    )
                except (ValueError, TypeError):
                    challenge["timestamp"] = None
            elif not isinstance(challenge.get("timestamp"), datetime):
                challenge["timestamp"] = None

            challenges_processed.append(challenge)

        # logger.info("Active challenges count: %d", len(challenges_processed)) # Reduce log noise
        return challenges_processed
    except sqlite3.Error:
        logger.exception("Error fetching active challenges.")
        return []


def get_completed_challenges(limit=50):
    """
    Returns a list of completed challenges with player names and score details
    """
    db = get_db()
    try:
        # Use the view we created to get completed challenges with player names and score
        cur = db.execute(
            "SELECT * FROM completed_challenges_view LIMIT ?",
            (limit,),
        )
        challenges_raw = cur.fetchall()
        challenges_processed = []
        # Process dates for completed challenges as well
        for row in challenges_raw:
            challenge = dict(row)
            if isinstance(challenge.get("resolved_at"), str):
                try:
                    resolved_at_str = challenge["resolved_at"].split(".")[0]
                    challenge["resolved_at"] = datetime.strptime(
                        resolved_at_str, "%Y-%m-%d %H:%M:%S"
                    )
                except (ValueError, TypeError):
                    challenge["resolved_at"] = None
            elif not isinstance(challenge.get("resolved_at"), datetime):
                challenge["resolved_at"] = None

            if isinstance(challenge.get("timestamp"), str):
                try:
                    timestamp_str = challenge["timestamp"].split(".")[0]
                    challenge["timestamp"] = datetime.strptime(
                        timestamp_str, "%Y-%m-%d %H:%M:%S"
                    )
                except (ValueError, TypeError):
                    challenge["timestamp"] = None
            elif not isinstance(challenge.get("timestamp"), datetime):
                challenge["timestamp"] = None

            # Format resolved_at for display if needed elsewhere, or do it in template
            if challenge.get("resolved_at"):
                challenge["resolved_at_fmt"] = challenge["resolved_at"].strftime(
                    "%Y-%m-%d %H:%M"
                )
            else:
                challenge["resolved_at_fmt"] = "N/A"

            challenges_processed.append(challenge)

        # logger.info("Completed challenges retrieved: %d", len(challenges_processed)) # Reduce log noise
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
        cur = db.execute(
            "SELECT * FROM players WHERE available = 0 ORDER BY rank ASC"
        )  # Added order by rank
        players = cur.fetchall()

        # Format unavailable_since dates for display
        players_with_formatted_dates = []

        for player in players:
            p = dict(player)  # Convert to dict for modification
            # Format unavailable_since for display
            if p.get("unavailable_since"):
                try:
                    unav_dt = p["unavailable_since"]
                    if isinstance(unav_dt, str):
                        unav_dt_str = unav_dt.split(".")[0]
                        unav_dt = datetime.strptime(unav_dt_str, "%Y-%m-%d %H:%M:%S")
                    elif not isinstance(unav_dt, datetime):
                        raise TypeError("unavailable_since is not a recognized type")

                    # Format as simple string without brackets
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
            "SELECT * FROM players WHERE block_challenger_until IS NOT NULL AND block_challenger_until > ? ORDER BY rank ASC",  # Added order by rank
            (now,),
        )
        players = cur.fetchall()

        # Format block dates for display
        now_dt = get_current_time()
        players_with_formatted_dates = []

        for player in players:
            p = dict(player)  # Convert to dict for modification
            # Format block_challenger_until for display
            if p.get("block_challenger_until"):
                try:
                    block_dt = p["block_challenger_until"]
                    if isinstance(block_dt, str):
                        block_dt_str = block_dt.split(".")[0]
                        block_dt = datetime.strptime(block_dt_str, "%Y-%m-%d %H:%M:%S")
                    elif not isinstance(block_dt, datetime):
                        raise TypeError(
                            "block_challenger_until is not a recognized type"
                        )

                    # Format as simple string without brackets
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
            "SELECT * FROM players WHERE block_opponent_until IS NOT NULL AND block_opponent_until > ? ORDER BY rank ASC",  # Added order by rank
            (now,),
        )
        players = cur.fetchall()

        # Format block dates for display
        now_dt = get_current_time()
        players_with_formatted_dates = []

        for player in players:
            p = dict(player)  # Convert to dict for modification
            # Format block_opponent_until for display
            if p.get("block_opponent_until"):
                try:
                    block_dt = p["block_opponent_until"]
                    if isinstance(block_dt, str):
                        block_dt_str = block_dt.split(".")[0]
                        block_dt = datetime.strptime(block_dt_str, "%Y-%m-%d %H:%M:%S")
                    elif not isinstance(block_dt, datetime):
                        raise TypeError("block_opponent_until is not a recognized type")

                    # Format as simple string without brackets
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
    now_dt = get_current_time()  # Get current datetime object
    now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")  # String version for DB queries
    active_ids = get_active_challenge_ids()

    # --- NEW RULE: Players from rank 11 onwards cannot challenge upwards if they are blocked as a challenger ---
    if challenger_rank >= 11:
        is_challenger_blocked = False
        if challenger["block_challenger_until"]:
            try:
                block_dt = challenger["block_challenger_until"]
                # Ensure block_dt is a datetime object for comparison
                if isinstance(block_dt, str):
                    # Handle potential fractional seconds from Python's strftime
                    block_dt_str = block_dt.split(".")[0]
                    block_dt = datetime.strptime(block_dt_str, "%Y-%m-%d %H:%M:%S")

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
            return (
                []
            )  # Return empty list if challenger (rank 11+) is blocked from initiating challenges
    # --- END NEW RULE ---

    # Rule: Top 10 can challenge anyone above them
    # This group is not affected by the new "rank 11+ and blocked" rule for upward challenges.
    # General block status (if they can challenge at all) is handled by the /challenge route and dropdown population.
    if challenger_rank <= 10:
        query = (
            "SELECT * FROM players WHERE rank < ? AND available = 1 "
            "AND id != ? "  # Cannot challenge self
            "AND (block_opponent_until IS NULL OR block_opponent_until <= ?) ORDER BY rank ASC"
        )
        parameters = (challenger_rank, challenger["id"], now_str)
        cur = db.execute(query, parameters)
        eligible = cur.fetchall()
        # Filter out players already in an active challenge
        eligible = [p for p in eligible if p["id"] not in active_ids]
        # logger.info("Eligible opponents for rank %s (<=10): %d", challenger_rank, len(eligible))
        return eligible

    # Rule: Ranks 11-36 challenge based on rank difference bands
    # This section is now implicitly guarded: if challenger_rank >= 11 and they were blocked,
    # the function would have returned [] already.
    if 11 <= challenger_rank <= 15:
        max_rank_diff = 4  # Can challenge up to 4 ranks higher
    elif 16 <= challenger_rank <= 21:
        max_rank_diff = 5  # Can challenge up to 5 ranks higher
    elif 22 <= challenger_rank <= 28:
        max_rank_diff = 6  # Can challenge up to 6 ranks higher
    elif 29 <= challenger_rank <= 36:
        max_rank_diff = 7  # Can challenge up to 7 ranks higher
    else:  # Should not happen if rank is always >= 1
        max_rank_diff = 0

    # Original min rank to challenge
    original_min_eligible_rank = max(1, challenger_rank - max_rank_diff)

    # Count unavailable players in the normal range
    query_unavailable_count = (
        "SELECT COUNT(*) as unavailable_count FROM players "
        "WHERE rank >= ? AND rank < ? AND available = 0"
    )
    cur = db.execute(
        query_unavailable_count, (original_min_eligible_rank, challenger_rank)
    )
    unavailable_count = cur.fetchone()["unavailable_count"]

    # Adjust min rank to include additional players to compensate for unavailable ones
    # But never go below rank 1
    adjusted_min_eligible_rank = max(1, original_min_eligible_rank - unavailable_count)

    # Query eligible opponents with adjusted range
    query = (
        "SELECT * FROM players WHERE rank >= ? AND rank < ? AND available = 1 "
        "AND id != ? "  # Cannot challenge self
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

    # Filter out players already in an active challenge
    eligible = [p for p in eligible if p["id"] not in active_ids]

    # logger.info(
    #     "Eligible opponents for rank %s (>=11): %d (Adjusted range %d-%d, Unavailable: %d)",
    #     challenger_rank, len(eligible), adjusted_min_eligible_rank, challenger_rank - 1, unavailable_count
    # )
    return eligible


# --- Utility function for re-ranking ---
def rerank_players(
    db, allow_temporary_overflow=False
):  # Added allow_temporary_overflow
    """
    Re-assigns ranks 1 to N based on the current order (rank ASC, is_new DESC, id ASC).
    Deletes players ranked > 36 after re-ranking, unless allow_temporary_overflow is True.
    Should be called within a transaction.
    """
    try:
        cur = db.execute(
            "SELECT id FROM players ORDER BY rank ASC, is_new DESC, id ASC"
        )
        players_to_rerank = cur.fetchall()

        new_rank_value = 1
        # ids_ranked set was redundant as SELECT already gives unique IDs in order.
        for row in players_to_rerank:
            db.execute(
                "UPDATE players SET rank = ? WHERE id = ?",
                (new_rank_value, row["id"]),
            )
            new_rank_value += 1

        # Remove players pushed beyond rank 36 (if any)
        final_player_count = new_rank_value - 1

        if not allow_temporary_overflow and final_player_count > 36:
            logger.warning(
                f"Re-ranking resulted in {final_player_count} players. Deleting ranks > 36."
            )
            deleted_count = db.execute("DELETE FROM players WHERE rank > 36").rowcount
            logger.info(f"Deleted {deleted_count} players with rank > 36.")
        elif allow_temporary_overflow and final_player_count > 36:
            logger.info(
                f"Re-ranking resulted in {final_player_count} players. Temporary overflow allowed."
            )
        # If not allow_temporary_overflow and final_player_count <= 36, no deletion needed.
        # If allow_temporary_overflow and final_player_count <= 36, no deletion needed.

    except sqlite3.Error as e:
        logger.exception("Error during player re-ranking.")
        raise e  # Re-raise to ensure transaction rollback if called within 'with db:'


# --------------- ROUTES ---------------
@app.route("/")
def home():
    return redirect(url_for("stecher_start"))


@app.route("/stecher_start")
def stecher_start():
    # Simple start page, no DB access needed yet
    return render_template("stecher_start.html")


@app.route("/index")
def index():
    try:
        db = get_db()
        now_dt = get_current_time()  # Get current datetime object
        now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")  # String version for DB queries

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
            ORDER BY rank ASC
            """,
            (now_str,),
        )
        players = cur.fetchall()
        players_list = []

        for p_row in players:
            p = dict(p_row)  # Convert Row object to dict for modification
            p["blocked_challenger"] = False
            p["blocked_opponent"] = False
            p["block_challenger_until_fmt"] = None  # Initialize format fields
            p["block_opponent_until_fmt"] = None
            p["unavailable_since_fmt"] = None

            # Check block_challenger_until
            if p.get("block_challenger_until"):
                try:
                    block_until_dt = p["block_challenger_until"]
                    # SQLite stores DATETIME as TEXT, ISO format is default
                    if isinstance(block_until_dt, str):
                        # Handle potential fractional seconds from Python's strftime
                        block_until_dt_str = block_until_dt.split(".")[0]
                        block_until_dt = datetime.strptime(
                            block_until_dt_str, "%Y-%m-%d %H:%M:%S"
                        )
                    # Check if it's already a datetime object (if detect_types worked)
                    elif not isinstance(block_until_dt, datetime):
                        raise TypeError(
                            "block_challenger_until is not a recognized type"
                        )

                    if now_dt < block_until_dt:
                        p["blocked_challenger"] = True
                        # Format for display - without brackets
                        p["block_challenger_until_fmt"] = block_until_dt.strftime(
                            "%Y-%m-%d %H:%M"
                        )
                    # No need to clear expired block here, boolean flag is enough

                except (ValueError, TypeError, AttributeError) as e:
                    logger.warning(
                        f"Could not parse or compare block_challenger_until for player {p['id']}: {p['block_challenger_until']} - Error: {e}"
                    )
                    # Keep boolean as False, fmt as None (fmt = default formatting mechanism should be used)

            # Check block_opponent_until
            if p.get("block_opponent_until"):
                try:
                    block_until_dt = p["block_opponent_until"]
                    if isinstance(block_until_dt, str):
                        block_until_dt_str = block_until_dt.split(".")[0]
                        block_until_dt = datetime.strptime(
                            block_until_dt_str, "%Y-%m-%d %H:%M:%S"
                        )
                    elif not isinstance(block_until_dt, datetime):
                        raise TypeError("block_opponent_until is not a recognized type")

                    if now_dt < block_until_dt:
                        p["blocked_opponent"] = True
                        p["block_opponent_until_fmt"] = block_until_dt.strftime(
                            "%Y-%m-%d %H:%M"
                        )

                except (ValueError, TypeError, AttributeError) as e:
                    logger.warning(
                        f"Could not parse or compare block_opponent_until for player {p['id']}: {p['block_opponent_until']} - Error: {e}"
                    )

            # Format unavailable_since for display
            if p.get("unavailable_since"):
                try:
                    unav_dt = p["unavailable_since"]
                    if isinstance(unav_dt, str):
                        unav_dt_str = unav_dt.split(".")[0]
                        unav_dt = datetime.strptime(unav_dt_str, "%Y-%m-%d %H:%M:%S")
                    elif not isinstance(unav_dt, datetime):
                        raise TypeError("unavailable_since is not a recognized type")
                    p["unavailable_since_fmt"] = unav_dt.strftime("%Y-%m-%d %H:%M")
                except (ValueError, TypeError, AttributeError) as e:
                    logger.warning(
                        f"Could not parse unavailable_since for player {p['id']}: {p['unavailable_since']} - Error: {e}"
                    )
                    p["unavailable_since_fmt"] = "Ungültig"

            players_list.append(p)

        pyramid_data = create_pyramid(players_list)
        active_challenges_data = get_active_challenges()  # Already processes dates
        completed_challenges_data = (
            get_completed_challenges()
        )  # Already processes dates
        blocked_challenger_players_data = (
            get_blocked_challenger_players()
        )  # Now includes formatted dates
        blocked_opponent_players_data = (
            get_blocked_opponent_players()
        )  # Now includes formatted dates
        unavailable_players_data = (
            get_unavailable_players()
        )  # Now includes formatted dates

        # logger.info(
        #     "Rendering index: players=%d, pyramid rows=%d", len(players_list), len(pyramid_data)
        # )
        return render_template(
            "index.html",
            pyramid=pyramid_data,
            players=players_list,  # Contains formatted dates
            active_challenges=active_challenges_data,  # Contains datetime objects
            completed_challenges=completed_challenges_data,  # Contains datetime objects
            blocked_challenger_players=blocked_challenger_players_data,  # Now includes formatted dates
            blocked_opponent_players=blocked_opponent_players_data,  # Now includes formatted dates
            unavailable_players=unavailable_players_data,  # Now includes formatted dates
        )
    except sqlite3.Error as db_err:
        logger.exception("Database error on /index route.")
        flash(
            "Ein Datenbankfehler ist aufgetreten. Bitte versuchen Sie es später erneut.",
            "danger",
        )
        # Render a simpler error page or redirect
        return render_template("error.html", error_message="Datenbankfehler"), 500
    except Exception as e:
        logger.exception("Unexpected error on /index route.")
        flash("Ein unerwarteter Fehler ist aufgetreten.", "danger")
        return render_template("error.html", error_message="Unerwarteter Fehler"), 500


@app.route("/admin")
def admin():
    """
    Displays the admin page for managing pending challenges.
    """
    db = get_db()
    try:
        # Fetch unresolved challenges, ordered by deadline
        cur = db.execute(
            "SELECT c.*, p1.name as challenger_name, p2.name as opponent_name FROM challenges c "
            "JOIN players p1 ON c.challenger_id = p1.id "
            "JOIN players p2 ON c.opponent_id = p2.id "
            "WHERE c.resolved = 0 ORDER BY c.deadline ASC"
        )
        challenges_raw = cur.fetchall()
        challenges_processed = []
        for row in challenges_raw:
            challenge = dict(row)  # Convert Row to dict
            # Ensure deadline is a datetime object for the template
            if isinstance(challenge.get("deadline"), str):
                try:
                    # Handle potential fractional seconds if they exist
                    deadline_str = challenge["deadline"].split(".")[0]
                    challenge["deadline"] = datetime.strptime(
                        deadline_str, "%Y-%m-%d %H:%M:%S"
                    )
                except (ValueError, TypeError):
                    logger.warning(
                        f"Could not parse deadline string '{challenge['deadline']}' for challenge ID {challenge.get('id')}. Setting to None."
                    )
                    challenge["deadline"] = None  # Set to None if parsing fails
            elif not isinstance(challenge.get("deadline"), datetime):
                # If it's neither string nor datetime, treat as invalid
                logger.warning(
                    f"Unexpected type for deadline '{type(challenge.get('deadline'))}' for challenge ID {challenge.get('id')}. Setting to None."
                )
                challenge["deadline"] = None

            challenges_processed.append(challenge)

        # logger.info("Rendering admin: challenges=%d", len(challenges_processed))
        return render_template(
            "admin.html", challenges=challenges_processed
        )  # Pass processed list
    except sqlite3.Error as e:
        logger.exception("Database error on /admin route.")
        flash(
            "Ein Datenbankfehler ist aufgetreten beim Laden der Admin-Seite.", "danger"
        )
        # Redirect to index on DB error, as admin page is unusable
        return redirect(url_for("index"))
    except Exception as e:
        logger.exception("Unexpected error on /admin route.")
        flash("Ein unerwarteter Fehler ist aufgetreten.", "danger")
        # Redirect to index on other errors
        return redirect(url_for("index"))


@app.route("/get_players")
def get_players():
    db = get_db()
    try:
        cur = db.execute("SELECT * FROM players ORDER BY rank ASC")
        players = cur.fetchall()
        active_ids = get_active_challenge_ids()
        current_time = get_current_time()
        players_list = []
        for p_row in players:
            p = dict(p_row)  # Convert to dict
            block_challenger = False
            block_opponent = False
            block_challenger_until_str = None
            block_opponent_until_str = None
            unavailable_since_str = None

            # Check block_challenger_until
            if p.get("block_challenger_until"):
                try:
                    block_until = p["block_challenger_until"]
                    if isinstance(block_until, str):
                        block_until_dt_str = block_until.split(".")[0]
                        block_until = datetime.strptime(
                            block_until_dt_str, "%Y-%m-%d %H:%M:%S"
                        )
                    elif not isinstance(block_until, datetime):
                        raise TypeError("block_challenger_until is not datetime")

                    if current_time < block_until:
                        block_challenger = True
                        block_challenger_until_str = block_until.strftime(
                            "%Y-%m-%d %H:%M"
                        )  # Keep formatted string for potential display

                except (ValueError, TypeError, AttributeError):
                    pass  # Ignore parsing errors

            # Check block_opponent_until
            if p.get("block_opponent_until"):
                try:
                    block_until = p["block_opponent_until"]
                    if isinstance(block_until, str):
                        block_until_dt_str = block_until.split(".")[0]
                        block_until = datetime.strptime(
                            block_until_dt_str, "%Y-%m-%d %H:%M:%S"
                        )
                    elif not isinstance(block_until, datetime):
                        raise TypeError("block_opponent_until is not datetime")

                    if current_time < block_until:
                        block_opponent = True
                        block_opponent_until_str = block_until.strftime(
                            "%Y-%m-%d %H:%M"
                        )  # Keep formatted string for potential display
                except (ValueError, TypeError, AttributeError):
                    pass  # Ignore parsing errors

            # Format unavailable_since
            if p.get("unavailable_since"):
                try:
                    unav_dt = p["unavailable_since"]
                    if isinstance(unav_dt, str):
                        unav_dt_str = unav_dt.split(".")[0]
                        unav_dt = datetime.strptime(unav_dt_str, "%Y-%m-%d %H:%M:%S")
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
                    "rank": p["rank"],
                    "available": bool(p["available"]),
                    "unavailable_since": unavailable_since_str,  # Formatted string
                    "block_challenger": block_challenger,  # Boolean flag for logic
                    "block_opponent": block_opponent,  # Boolean flag for logic
                    "block_challenger_until": block_challenger_until_str,  # Formatted string or None
                    "block_opponent_until": block_opponent_until_str,  # Formatted string or None
                    "in_challenge": in_challenge,
                    "is_new": bool(p["is_new"]),
                }
            )
        # logger.info("get_players returning %d players", len(players_list)) # Reduce log noise
        return jsonify(players_list)
    except sqlite3.Error as e:
        logger.exception("Database error on /get_players route.")
        return jsonify({"error": "Database error"}), 500


@app.route("/eligible_opponents", methods=["POST"])
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

        # Check general block status for challenger (this is a general check,
        # specific "upward challenge block for rank 11+" is handled in eligible_opponents_for)
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
                if (
                    isinstance(block_dt, datetime) and now_dt < block_dt
                ):  # Ensure it's datetime before comparison
                    is_generally_blocked_as_challenger = True
                    block_until_fmt = block_dt.strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError, AttributeError):
                logger.warning(
                    f"Could not parse block_challenger_until for eligibility check: {challenger['block_challenger_until']}"
                )

        if is_generally_blocked_as_challenger:
            # This message might be superseded if eligible_opponents_for returns [] due to the new rule,
            # but it's a good general check.
            # The client will show "No opponents" if eligible_opponents_for returns []
            # If eligible_opponents_for returns opponents (e.g. rank <=10), but this block is active,
            # the /challenge route will still prevent it.
            pass  # No direct error here, let eligible_opponents_for decide.
            # The /challenge route has its own more direct block check.

        opponents = eligible_opponents_for(
            challenger
        )  # This now incorporates the new rule

        # If challenger is rank 11+ and blocked, opponents will be []
        # We can provide a more specific message if that's the case.
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
        ):  # Should not happen for rank <=10 unless no one is above them
            return (
                jsonify(
                    {
                        "error": f"{challenger['name']} ist bis {block_until_fmt} gesperrt."
                    }
                ),
                400,
            )

        opponents_list = []
        for opp in opponents:
            opponents_list.append(
                {
                    "id": opp["id"],
                    "name": opp["name"],
                    "rank": opp["rank"],
                    "available": bool(opp["available"]),
                }
            )
        # logger.info(
        #     "Eligible opponents for challenger %s (%s): %d", challenger_id, challenger['name'], len(opponents_list)
        # )
        return jsonify(opponents_list)
    except sqlite3.Error as e:
        logger.exception("Database error fetching eligible opponents.")
        return jsonify({"error": "Database error"}), 500
    except Exception as e:
        logger.exception("Unexpected error fetching eligible opponents.")
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500


@app.route("/challenge", methods=["POST"])
def challenge():
    challenger_id = request.form.get("challenger")
    opponent_id = request.form.get("opponent")
    if not challenger_id or not opponent_id:
        return jsonify({"error": "Both challenger and opponent must be selected."}), 400

    db = get_db()
    try:
        # --- Server-Side Validation ---
        cur = db.execute("SELECT * FROM players WHERE id = ?", (challenger_id,))
        challenger = cur.fetchone()
        cur = db.execute("SELECT * FROM players WHERE id = ?", (opponent_id,))
        opponent = cur.fetchone()

        if not challenger or not opponent:
            return jsonify({"error": "Invalid player selection."}), 400
        if challenger_id == opponent_id:
            return jsonify({"error": "Cannot challenge yourself."}), 400

        # Check availability and blocks
        now_dt = get_current_time()
        now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")  # For DB queries if needed

        if not challenger["available"]:
            return jsonify({"error": f"{challenger['name']} is not available."}), 400

        # Check challenger block (general block)
        challenger_blocked_general = False
        challenger_block_fmt = None
        if challenger["block_challenger_until"]:
            try:
                block_dt = challenger["block_challenger_until"]
                if isinstance(block_dt, str):
                    block_dt = datetime.strptime(
                        block_dt.split(".")[0], "%Y-%m-%d %H:%M:%S"
                    )
                if (
                    isinstance(block_dt, datetime) and now_dt < block_dt
                ):  # Ensure datetime before comparison
                    challenger_blocked_general = True
                    challenger_block_fmt = block_dt.strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError, AttributeError):
                pass  # Ignore parsing error

        if challenger_blocked_general:
            # This is a general block. The new rule in eligible_opponents_for handles specific upward challenge blocks.
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

        # Check opponent block
        opponent_blocked = False
        opponent_block_fmt = None
        if opponent["block_opponent_until"]:
            try:
                block_dt = opponent["block_opponent_until"]
                if isinstance(block_dt, str):
                    block_dt = datetime.strptime(
                        block_dt.split(".")[0], "%Y-%m-%d %H:%M:%S"
                    )
                if (
                    isinstance(block_dt, datetime) and now_dt < block_dt
                ):  # Ensure datetime
                    opponent_blocked = True
                    opponent_block_fmt = block_dt.strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError, AttributeError):
                pass  # Ignore parsing error
        if opponent_blocked:
            return (
                jsonify(
                    {
                        "error": f"{opponent['name']} is blocked from being challenged until {opponent_block_fmt}."
                    }
                ),
                400,
            )

        # Check if either player is already in an active challenge
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

        # Check if opponent is eligible for this challenger (re-check eligibility rules, including the new one)
        eligible_opponents_list = eligible_opponents_for(challenger)
        if opponent["id"] not in [p["id"] for p in eligible_opponents_list]:
            # Provide a more specific message if the challenger is rank 11+ and blocked (new rule)
            if (
                challenger["rank"] >= 11 and challenger_blocked_general
            ):  # Re-check general block for this specific message context
                return (
                    jsonify(
                        {
                            "error": f"{challenger['name']} (Rang {challenger['rank']}) ist bis {challenger_block_fmt} gesperrt und kann keine Aufstiegsspiele bestreiten. {opponent['name']} ist kein gültiger Gegner."
                        }
                    ),
                    400,
                )
            return (  # General eligibility failure
                jsonify(
                    {
                        "error": f"{opponent['name']} is not an eligible opponent for {challenger['name']}."
                    }
                ),
                400,
            )
        # --- End Server-Side Validation ---

        timestamp = get_current_time()
        deadline = timestamp + timedelta(days=10)
        db.execute(
            "INSERT INTO challenges (challenger_id, opponent_id, timestamp, deadline, resolved, score_details) VALUES (?, ?, ?, ?, ?, ?)",
            (
                challenger_id,
                opponent_id,
                timestamp,  # Store as datetime object
                deadline,  # Store as datetime object
                0,
                None,  # Score is null initially
            ),
        )
        db.commit()
        socketio.emit(
            "update", {"message": "New challenge created"}
        )  # Add simple payload
        message = f"Ich, {challenger['name']} (Rang {challenger['rank']}), fordere hiermit {opponent['name']} (Rang {opponent['rank']}) heraus."
        logger.info("Challenge created: %s vs %s", challenger["name"], opponent["name"])
        return jsonify(
            {"message": message, "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S")}
        )
    except sqlite3.Error as e:
        db.rollback()  # Rollback on error
        logger.exception("Database error during challenge creation.")
        return jsonify({"error": "Database error during challenge creation."}), 500
    except Exception as e:
        # Catch potential errors during validation (e.g., date parsing)
        logger.exception("Error during challenge validation or creation.")
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500


@app.route("/toggle_availability", methods=["POST"])
def toggle_availability():
    player_id = request.form.get("player_id")
    if not player_id:
        return jsonify({"success": False, "message": "No player_id provided."}), 400

    db = get_db()
    try:
        cur = db.execute("SELECT * FROM players WHERE id = ?", (player_id,))
        player = cur.fetchone()
        if not player:
            return jsonify({"success": False, "message": "Player not found."}), 404

        # Check if player is in an active challenge
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
        new_unavailable_since = None
        block_opponent_until = player[
            "block_opponent_until"
        ]  # Keep existing block unless overwritten

        now_dt = get_current_time()

        if new_availability == 0:  # Becoming unavailable
            new_unavailable_since = now_dt  # Store datetime object
            # Keep existing block_opponent_until if set
        else:  # Becoming available
            # Set a 3-day block only if they weren't already blocked for longer
            three_days_later = now_dt + timedelta(days=3)
            should_set_block = True
            if player["block_opponent_until"]:
                try:
                    current_block_dt = player["block_opponent_until"]
                    if isinstance(current_block_dt, str):
                        current_block_dt_str = current_block_dt.split(".")[0]
                        current_block_dt = datetime.strptime(
                            current_block_dt_str, "%Y-%m-%d %H:%M:%S"
                        )
                    elif not isinstance(current_block_dt, datetime):
                        raise TypeError("block_opponent_until is not datetime")

                    if current_block_dt > three_days_later:
                        should_set_block = False  # Keep the longer existing block
                except (ValueError, TypeError, AttributeError):
                    pass  # Ignore invalid date, proceed to set new block

            if should_set_block:
                block_opponent_until = three_days_later  # Store datetime object

        db.execute(
            "UPDATE players SET available = ?, unavailable_since = ?, block_opponent_until = ? WHERE id = ?",
            (new_availability, new_unavailable_since, block_opponent_until, player_id),
        )
        db.commit()
        socketio.emit("update", {"message": "Player availability toggled"})
        logger.info(
            "Toggled availability for player %s (%s) to %s",
            player_id,
            player["name"],
            new_availability,
        )
        # Return the actual new state for confirmation - format date as plain string without brackets
        block_opponent_until_fmt = None
        if block_opponent_until and isinstance(block_opponent_until, datetime):
            block_opponent_until_fmt = block_opponent_until.strftime("%Y-%m-%d %H:%M")

        return jsonify(
            {
                "success": True,
                "new_availability": new_availability,
                "block_opponent_until": block_opponent_until_fmt,
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
                {"success": False, "message": f"An unexpected error occurred: {e}"}
            ),
            500,
        )


@app.route("/submit_result", methods=["POST"])
def submit_result():
    # This route handles submissions from admin.html
    challenge_id = request.form.get("challenge_id")
    result = request.form.get(
        "result"
    )  # Dropdown: challenger_wins, opponent_wins, not_happened
    special_result = request.form.get(
        "special_result", ""
    )  # Aufgabe, Disqualifikation (Value from select)
    set1_score = request.form.get("set1_score", "").strip()
    set2_score = request.form.get("set2_score", "").strip()
    set3_score = request.form.get("set3_score", "").strip()

    if not challenge_id or not result:
        flash("Invalid submission: Missing challenge ID or result type.", "danger")
        # Redirect back to the admin page where the form was submitted
        return redirect(url_for("admin"))

    # --- Score Validation and Construction ---
    score_details = None
    if result == "not_happened":
        score_details = "Nicht stattgefunden"
    elif special_result in ["Aufgabe", "Disqualifikation"]:
        score_details = special_result
    else:
        if set1_score and set2_score:
            # Basic format validation (contains colon) - could be more strict
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
        elif (
            result != "not_happened"
        ):  # if result is win/loss but no scores and no special
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
    # --- End Score Validation ---

    db = get_db()
    try:
        cur = db.execute(
            "SELECT * FROM challenges WHERE id = ? AND resolved = 0", (challenge_id,)
        )
        challenge_record = cur.fetchone()
        if not challenge_record:
            flash("Challenge not found or already resolved.", "danger")
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

        # Clear any existing blocks before setting new ones
        db.execute(
            "UPDATE players SET block_challenger_until = NULL, block_opponent_until = NULL WHERE id IN (?, ?)",
            (challenger_id, opponent_id),
        )

        rank_changed = False  # Flag to check if re-ranking is needed

        if result == "challenger_wins":
            db.execute(
                "UPDATE players SET block_opponent_until = ? WHERE id = ?",  # Challenger (winner) is blocked as opponent
                (block_until, challenger_id),
            )
            db.execute(
                "UPDATE players SET block_challenger_until = ? WHERE id = ?",  # Opponent (loser) is blocked as challenger
                (block_until, opponent_id),
            )

            if challenger["rank"] > opponent["rank"]:
                rank_changed = True
                if challenger["is_new"] == 1:
                    new_rank = opponent["rank"]
                    db.execute(
                        "UPDATE players SET rank = rank + 1 WHERE rank >= ? AND rank <= 36 AND id != ?",  # Shift players down
                        (
                            new_rank,
                            challenger_id,
                        ),  # Exclude challenger from shift if they are already at target
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
                    # Shift players between new_rank (inclusive) and old_challenger_rank (exclusive) down by one
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
            else:  # Challenger won but was already higher ranked
                flash(f"{challenger['name']} gewinnt. Keine Rangänderung.", "info")
                if (
                    challenger["is_new"] == 1
                ):  # New player won against lower ranked (should not happen with rules) or same rank
                    db.execute(
                        "UPDATE players SET is_new = 0 WHERE id = ?", (challenger_id,)
                    )

        elif result == "opponent_wins":
            db.execute(
                "UPDATE players SET block_opponent_until = ? WHERE id = ?",  # Opponent (winner) is blocked as opponent
                (block_until, opponent_id),
            )
            db.execute(
                "UPDATE players SET block_challenger_until = ? WHERE id = ?",  # Challenger (loser) is blocked as challenger
                (block_until, challenger_id),
            )
            if challenger["is_new"] == 1:  # New player lost
                db.execute(
                    "UPDATE players SET is_new = 0 WHERE id = ?", (challenger_id,)
                )
            flash(f"Keine Rangänderung: {opponent['name']} gewinnt.", "info")

        elif result == "not_happened":
            # No blocks applied if game didn't happen
            if challenger["is_new"] == 1:  # New player challenge didn't happen
                db.execute(
                    "UPDATE players SET is_new = 0 WHERE id = ?", (challenger_id,)
                )
            flash(
                "Herausforderung als 'Nicht stattgefunden' markiert. Keine Rangänderung, keine neuen Sperren.",
                "info",
            )
        else:  # Should not be reached due to initial checks
            flash("Unbekanntes Ergebnis.", "danger")
            db.rollback()
            return redirect(url_for("admin"))

        # --- Re-ranking logic (Run only if ranks actually changed or a new player was involved and won) ---
        # After match resolution, always re-rank and enforce 36 player limit.
        with db:  # Use transaction for re-ranking
            rerank_players(
                db, allow_temporary_overflow=False
            )  # Enforce 36 player limit
        # db.commit() was part of the 'with db:' block for rerank_players

        socketio.emit("update", {"message": "Challenge resolved and ranks updated"})
        socketio.emit(
            "challenge_resolved", {"challenge_id": challenge_id}
        )  # Specific event for client-side color clearing
    except sqlite3.Error as e:
        db.rollback()
        logger.exception(f"Database error during challenge result submission: {e}")
        flash(f"Internal error while updating challenge result: {e}", "danger")
    except Exception as e:
        db.rollback()
        logger.exception(f"Unexpected error during challenge result submission: {e}")
        flash(f"An unexpected error occurred: {e}", "danger")

    # Redirect back to the admin page after processing
    return redirect(url_for("admin"))


@app.route("/newplayer_challenge", methods=["POST"])
def newplayer_challenge():
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

        original_opponent_name = opponent["name"]  # Store for messages

        if not (11 <= opponent["rank"] <= 35):
            return (
                jsonify({"error": "Gegner muss initial zwischen Rang 11 und 35 sein."}),
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
            # Insert new player with a placeholder rank (e.g., 99) and is_new=1
            cursor = db.execute(
                "INSERT INTO players (name, available, rank, unavailable_since, is_new) VALUES (?, ?, ?, ?, ?)",
                (
                    newplayer_name,
                    1,
                    99,
                    None,
                    1,
                ),  # rank 99 ensures they are at the bottom initially
            )
            newplayer_id = cursor.lastrowid
            if not newplayer_id:  # Should not happen if insert was successful
                raise sqlite3.Error(
                    "Konnte die ID des neuen Spielers nicht abrufen nach dem Einfügen."
                )
            logger.info(
                f"New player '{newplayer_name}' inserted with temporary ID {newplayer_id} and rank 99."
            )

            # Re-rank players, allowing temporary overflow (e.g., 37 players)
            # This ensures the new player gets a sequential rank without being immediately deleted.
            rerank_players(db, allow_temporary_overflow=True)
            logger.info(
                f"Players re-ranked (allowing overflow). New player '{newplayer_name}' (ID: {newplayer_id}) now has a final rank."
            )

            # Fetch the new player's data after re-ranking to ensure they exist
            cur_new_player_check = db.execute(
                "SELECT * FROM players WHERE id = ?", (newplayer_id,)
            )
            new_player_after_rerank = cur_new_player_check.fetchone()
            if not new_player_after_rerank:
                # This should ideally not happen with allow_temporary_overflow=True
                logger.error(
                    f"New player '{newplayer_name}' (ID: {newplayer_id}) was unexpectedly deleted during re-ranking. Rolling back."
                )
                raise sqlite3.Error(
                    f"Der neue Spieler '{newplayer_name}' konnte nicht korrekt der Rangliste hinzugefügt werden. Bitte versuchen Sie es erneut."
                )

            # Fetch opponent data AGAIN after re-ranking to ensure they still exist
            # and to get their potentially updated rank for the message.
            cur_opponent_after_rerank = db.execute(
                "SELECT * FROM players WHERE id = ?", (opponent_id,)
            )
            opponent_after_rerank = cur_opponent_after_rerank.fetchone()

            if not opponent_after_rerank:
                # This check is a safeguard, though less likely if overflow is allowed.
                logger.error(
                    f"Opponent (ID: {opponent_id}, Name: {original_opponent_name}) was deleted during re-ranking (even with overflow allowed). This is unexpected. Rolling back."
                )
                raise sqlite3.Error(
                    f"Der ausgewählte Gegner ({original_opponent_name}) ist nach der Ranglistenanpassung nicht mehr verfügbar. Die Herausforderung kann nicht erstellt werden und der neue Spieler wurde NICHT hinzugefügt."
                )

            deadline = timestamp + timedelta(days=10)
            db.execute(
                "INSERT INTO challenges (challenger_id, opponent_id, timestamp, deadline, resolved, score_details) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    newplayer_id,  # This ID should now be valid
                    opponent_id,
                    timestamp,
                    deadline,
                    0,
                    None,
                ),
            )
            logger.info(
                f"Challenge created between new player {newplayer_id} ('{newplayer_name}') and opponent {opponent_id} ('{opponent_after_rerank['name']}')."
            )

            opponent_name_for_message = opponent_after_rerank["name"]
            opponent_new_rank = opponent_after_rerank["rank"]
            new_player_current_rank = new_player_after_rerank[
                "rank"
            ]  # Get new player's actual rank for message

        # This part is executed only if the 'with db:' block completed successfully (committed)
        socketio.emit("update", {"message": "New player added and challenged"})
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
        return jsonify(
            {"message": message, "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S")}
        )

    except sqlite3.IntegrityError as e:
        # db.rollback() is handled by 'with db:' if the error originated from within it.
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
            # This error means either newplayer_id or opponent_id was invalid.
            # With the new logic, newplayer_id should be preserved.
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
        # This catches other SQLite errors, including ones raised manually.
        logger.exception(
            f"SQLite error during new player challenge: '{str(e)}'. newplayer_name='{newplayer_name}', opponent_id='{opponent_id_str}'"
        )
        # Return the specific message if it's one of our custom `raise sqlite3.Error(...)`
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
        return jsonify({"error": f"Ein unerwarteter Fehler ist aufgetreten: {e}"}), 500


# --- Admin Player Management Routes (for db_settings.html) ---


@app.route("/add_player", methods=["POST"])
def add_player():
    """Adds a new player via the admin settings page."""
    data = request.get_json()
    if not data or "name" not in data or "rank" not in data:
        return jsonify({"success": False, "message": "Missing required fields."}), 400

    new_name = data["name"].strip()
    try:
        new_rank = int(data["rank"])
    except ValueError:
        return jsonify({"success": False, "message": "Invalid rank."}), 400

    # Validation
    if len(new_name) < 3:  # Basic length check
        return (
            jsonify(
                {"success": False, "message": "Name must be at least 3 characters."}
            ),
            400,
        )
    if not (1 <= new_rank <= 36):  # Admin can only add within 1-36 initially
        return (
            jsonify({"success": False, "message": "Rank must be between 1 and 36."}),
            400,
        )

    db = get_db()
    try:
        # Check for duplicate name (case-insensitive)
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

        with db:  # Use transaction
            # Insert player with the given rank, available, not new
            db.execute(
                "INSERT INTO players (name, available, rank, is_new) VALUES (?, ?, ?, ?)",
                (new_name, 1, new_rank, 0),  # available=1, is_new=0 for admin adds
            )
            logger.info(
                f"Admin added player '{new_name}' with initial rank {new_rank}."
            )

            # Re-rank ALL players to ensure consistency and enforce 36 player limit
            rerank_players(db, allow_temporary_overflow=False)
            logger.info("Re-ranked players after admin add, enforcing 36 player limit.")

        socketio.emit("update", {"message": f"Player {new_name} added"})
        return jsonify(
            {
                "success": True,
                "message": f"Player '{new_name}' added successfully. Ranks recalculated.",
            }
        )

    except sqlite3.IntegrityError as e:
        # db.rollback() handled by 'with db:'
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
        # db.rollback() handled by 'with db:'
        logger.exception(f"Error adding player {new_name} via admin: {e}")
        return jsonify({"success": False, "message": "Database error."}), 500
    except Exception as e:
        # db.rollback() handled by 'with db:'
        logger.exception(f"Unexpected error adding player {new_name} via admin: {e}")
        return (
            jsonify(
                {"success": False, "message": f"An unexpected error occurred: {e}"}
            ),
            500,
        )


@app.route("/update_player", methods=["POST"])
def update_player():
    """Updates player name and rank via the admin settings page."""
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
    if not (1 <= new_rank <= 36):  # Admin can only update within 1-36
        return (
            jsonify({"success": False, "message": "Rank must be between 1 and 36."}),
            400,
        )

    db = get_db()
    try:
        # Check if player exists
        cur = db.execute("SELECT rank, name FROM players WHERE id = ?", (player_id,))
        player = cur.fetchone()
        if not player:
            return jsonify({"success": False, "message": "Player not found."}), 404

        old_name = player["name"]

        # Check for duplicate name (excluding self, case-insensitive)
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

        with db:  # Use transaction
            # Update only name and rank, keep existing block statuses
            db.execute(
                "UPDATE players SET name = ?, rank = ? WHERE id = ?",
                (new_name, new_rank, player_id),
            )
            logger.info(
                f"Admin updated player {player_id}. Name: {new_name}, Rank attempt: {new_rank}. Preserved blocks."
            )

            # Re-rank ALL players to ensure consistency and enforce 36 player limit
            rerank_players(db, allow_temporary_overflow=False)
            logger.info(
                "Re-ranked players after admin update, enforcing 36 player limit."
            )

        socketio.emit("update", {"message": "Player details updated"})
        return jsonify(
            {
                "success": True,
                "message": "Player updated successfully. Ranks recalculated.",
            }
        )

    except sqlite3.IntegrityError as e:
        # db.rollback() handled by 'with db:'
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
        # db.rollback() handled by 'with db:'
        logger.exception(f"Error updating player {player_id} via admin: {e}")
        return jsonify({"success": False, "message": "Database error."}), 500
    except Exception as e:
        # db.rollback() handled by 'with db:'
        logger.exception(f"Unexpected error updating player {player_id} via admin: {e}")
        return (
            jsonify(
                {"success": False, "message": f"An unexpected error occurred: {e}"}
            ),
            500,
        )


@app.route("/delete_player", methods=["POST"])
def delete_player():
    """Deletes a player via the admin settings page."""
    data = request.get_json()
    if not data or "id" not in data:
        return jsonify({"success": False, "message": "Missing player id."}), 400

    player_id = data["id"]
    db = get_db()
    try:
        # Check if player exists
        cur = db.execute("SELECT name FROM players WHERE id = ?", (player_id,))
        player = cur.fetchone()
        if not player:
            return jsonify({"success": False, "message": "Player not found."}), 404

        player_name = player["name"]

        with db:  # Transaction for deletion and re-ranking
            # Delete the player (challenges cascade delete due to schema)
            player_deleted = db.execute(
                "DELETE FROM players WHERE id = ?", (player_id,)
            ).rowcount
            if player_deleted == 0:  # Should not happen if player was found
                raise sqlite3.Error(
                    "Player could not be deleted after existence check."
                )
            logger.info(f"Admin deleted player {player_id} ({player_name}).")

            # Re-rank remaining players and enforce 36 player limit
            rerank_players(db, allow_temporary_overflow=False)
            logger.info(
                "Re-ranked players after admin delete, enforcing 36 player limit."
            )

        socketio.emit("update", {"message": f"Player {player_name} deleted"})
        return jsonify(
            {
                "success": True,
                "message": f"Player '{player_name}' deleted successfully. Ranks recalculated.",
            }
        )

    except sqlite3.Error as e:
        # db.rollback() handled by 'with db:'
        logger.exception(
            f"Error deleting player {player_id} ({player_name if 'player_name' in locals() else 'N/A'}): {e}"
        )
        return (
            jsonify({"success": False, "message": "Database error during deletion."}),
            500,
        )
    except Exception as e:
        # db.rollback() handled by 'with db:'
        logger.exception(f"Unexpected error deleting player {player_id}: {e}")
        return (
            jsonify(
                {"success": False, "message": f"An unexpected error occurred: {e}"}
            ),
            500,
        )


@app.route("/set_player_block_status", methods=["POST"])
def set_player_block_status():
    """Sets the block status for a player via the admin settings page."""
    data = request.get_json()
    if not data or "player_id" not in data or "block_type" not in data:
        return jsonify({"success": False, "message": "Missing required fields."}), 400

    player_id = data["player_id"]
    block_type = data["block_type"]  # Expected values: 'none', 'challenger', 'opponent'

    if block_type not in ["none", "challenger", "opponent"]:
        return (
            jsonify({"success": False, "message": "Invalid block type specified."}),
            400,
        )

    db = get_db()
    try:
        # Check if player exists
        cur = db.execute("SELECT id, name FROM players WHERE id = ?", (player_id,))
        player = cur.fetchone()
        if not player:
            return jsonify({"success": False, "message": "Player not found."}), 404

        player_name = player["name"]
        now = get_current_time()
        # Use the same block duration as in submit_result
        block_duration = timedelta(days=7)
        block_until = now + block_duration

        with db:  # Use transaction
            if block_type == "none":
                db.execute(
                    "UPDATE players SET block_challenger_until = NULL, block_opponent_until = NULL WHERE id = ?",
                    (player_id,),
                )
                log_msg = f"Admin cleared block status for player {player_id} ({player_name})."
            elif block_type == "challenger":
                db.execute(
                    "UPDATE players SET block_challenger_until = ?, block_opponent_until = NULL WHERE id = ?",
                    (block_until, player_id),
                )
                log_msg = f"Admin set player {player_id} ({player_name}) as blocked challenger until {block_until}."
            elif block_type == "opponent":
                db.execute(
                    "UPDATE players SET block_opponent_until = ?, block_challenger_until = NULL WHERE id = ?",
                    (block_until, player_id),
                )
                log_msg = f"Admin set player {player_id} ({player_name}) as blocked opponent until {block_until}."

        logger.info(log_msg)
        socketio.emit("update", {"message": f"Block status updated for {player_name}"})
        return jsonify(
            {"success": True, "message": f"Block status for '{player_name}' updated."}
        )

    except sqlite3.Error as e:
        # db.rollback() handled by 'with db:'
        logger.exception(f"Error setting block status for player {player_id}: {e}")
        return jsonify({"success": False, "message": "Database error."}), 500
    except Exception as e:
        # db.rollback() handled by 'with db:'
        logger.exception(
            f"Unexpected error setting block status for player {player_id}: {e}"
        )
        return (
            jsonify(
                {"success": False, "message": f"An unexpected error occurred: {e}"}
            ),
            500,
        )


# --- NEW: Database Reset Route ---
@app.route("/reset_database", methods=["POST"])
def reset_database():
    """
    Resets the database by dropping existing tables and re-initializing
    from schema.sql and initial_players.json.
    """
    db = get_db()
    try:
        with db:  # Use transaction for the whole reset process
            logger.warning("Attempting database reset...")
            # Drop existing tables and view
            db.execute("DROP VIEW IF EXISTS completed_challenges_view;")
            db.execute("DROP TABLE IF EXISTS challenges;")
            db.execute("DROP TABLE IF EXISTS players;")
            logger.info("Existing tables dropped.")

            # --- Recreate Schema ---
            logger.info("Re-initializing schema...")
            schema_path = os.path.join(app.root_path, "schema.sql")
            with app.open_resource(schema_path) as f:
                db.executescript(f.read().decode("utf8"))
            logger.info("Database schema re-initialized.")

            # --- Load Initial Data ---
            logger.info("Loading initial players...")
            json_path = os.path.join(app.root_path, "initial_players.json")
            with open(json_path, encoding="utf8") as json_file:
                data = json.load(json_file)
                for player in data["players"]:
                    try:
                        db.execute(
                            "INSERT INTO players (id, name, available, rank, unavailable_since, is_new) VALUES (?, ?, ?, ?, ?, ?)",
                            (
                                player["id"],
                                player["name"],
                                int(player["is_available"]),
                                player["rank"],
                                None,
                                0,
                            ),
                        )
                    except sqlite3.IntegrityError:
                        logger.warning(
                            f"Initial player name '{player['name']}' might already exist during reset. Skipping."
                        )
            logger.info("Loaded initial players from JSON during reset.")

        # Commit happens automatically with 'with db:' if no exceptions occurred

        logger.info("Database reset successful.")
        # Emit Socket.IO event to notify all clients
        socketio.emit("database_reset", {"message": "Database has been reset."})
        return jsonify(
            {"success": True, "message": "Datenbank erfolgreich zurückgesetzt."}
        )

    except sqlite3.Error as e:
        # db.rollback() handled by 'with db:'
        logger.exception("Database error during reset.")
        return (
            jsonify(
                {"success": False, "message": f"Datenbankfehler beim Zurücksetzen: {e}"}
            ),
            500,
        )
    except Exception as e:
        # db.rollback() handled by 'with db:'
        logger.exception("Unexpected error during database reset.")
        return (
            jsonify(
                {
                    "success": False,
                    "message": f"Unerwarteter Fehler beim Zurücksetzen: {e}",
                }
            ),
            500,
        )


# --- Other Routes ---
@app.route("/db_settings")
def db_settings():
    # This is the player management admin page
    return render_template("db_settings.html")


@app.route("/initial_players")
def initial_players():
    # Placeholder for potential future initial player management page
    return render_template("initial_players.html")


# --- SocketIO Event Handlers ---
@socketio.on("connect")
def handle_connect():
    logger.info("Socket.IO client connected: %s", request.sid)


@socketio.on("disconnect")
def handle_disconnect():
    logger.info("Socket.IO client disconnected: %s", request.sid)


# Add error handlers for SocketIO
@socketio.on_error_default
def default_error_handler(e):
    logger.error(f"SocketIO Error: {e} from SID {request.sid}")


# --- Main Execution ---
if __name__ == "__main__":
    # Initialize DB within app context before running
    with app.app_context():
        init_db()  # This will now only initialize if needed

    logger.info("Starting Flask-SocketIO server with eventlet...")
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, use_reloader=True)
