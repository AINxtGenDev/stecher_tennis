# Tennis-Ranking Web Application 2026

<img src="static/01_tennis_racket.png" alt="Tennis Racket" width="300">

A comprehensive web-based tennis ranking management system with real-time updates, challenge management, and sophisticated player tracking.

## 🎯 Project Overview

The **Tennis Ranking Web Application** is a full-featured system for managing tennis players in a ranking-based tournament format. It provides real-time dynamic ranking updates, player blocking management, availability tracking, and advanced challenge scheduling with automatic rank adjustments based on match results.
This version (v3.60) introduces a robust authentication and authorization system, enhancing security and providing role-based access control for players, administrators, and super-administrators.

## 🛠 Core Technologies

- **Backend**: Python with the **Flask** web framework.
- **Real-time Communication**: **Flask-SocketIO** is used to push live data updates to all connected clients, ensuring the UI is always synchronized without needing page reloads.
- **Frontend**:
    - **HTML5** with Jinja2 templating.
    - **CSS**: **Bootstrap 5** for layout and styling, with significant custom CSS for a unique, 3D-effect look and feel.
    - **JavaScript**: **jQuery** for DOM manipulation and event handling, and the Socket.IO client library for real-time communication.
- **Database**: **SQLite 3**, with the schema defined in `schema.sql`.
- **Security**:
    - **bcrypt** for securely hashing user passwords.
    - **Flask-Login** for managing user sessions and authentication.
    - **Flask-WTF** for CSRF (Cross-Site Request Forgery) protection on all forms.

## ✨ Key Features

- **Player Ranking Pyramid**: The main page (`index.html`) displays players in a visual pyramid structure, clearly showing their current rank.
- **Authentication & Authorization**:
    - Secure login system (`login_tennis.html`).
    - Three user privilege levels: `player`, `admin`, and `superadmin`.
    - Navigation and features are dynamically shown/hidden based on the logged-in user's role.
- **Challenge System**:
    - Players can challenge others based on a set of rules (e.g., rank proximity).
    - The system enforces who can challenge whom.
    - Active challenges are displayed in a dedicated section.
- **New Player Integration**: A special workflow allows a new, unranked player to challenge an existing player (between ranks 11-44) to enter the pyramid.
- **Result Submission**: Admins can enter match results, including set scores and special outcomes like "Walkover" or "Disqualification." The system validates the score format.
- **Automatic Re-ranking**: Based on a challenge outcome, the system automatically adjusts player ranks. If a lower-ranked challenger wins, they take the opponent's rank, and all players in between are shifted down.
- **Player Availability**: Players can mark themselves as "unavailable," preventing them from being challenged. When they become available again, they are temporarily blocked from challenging higher-ranked players.
- **Player Blocking**: After a match, players are temporarily "blocked" (for 7 days) from challenging or being challenged by the same opponent to encourage variety.
- **Real-time UI**: All changes (new challenges, results, availability changes) are instantly reflected on the UIs of all connected users via WebSockets.
- **Administration Panels**:
    - **Admin (`admin.html`)**: View and manage all pending challenges.
    - **Super-Admin (`db_settings.html`)**: A powerful panel to:
        - Edit/delete any player.
        - Manually adjust player block status.
        - Change any user's password.
        - **Reset the entire database** to its initial state.

## Data Model (`schema.sql`)

The application uses a simple but effective database schema with two main tables and one view.

- **`players` table**:
    - Stores user credentials (`username`, `password_hash`), personal info (`name`, `rank`), and application state (`available`, `privilege_level`, `is_new`, `block_challenger_until`, `block_opponent_until`).
    - `is_new` flag tracks players who have just been added and are in their first challenge.
- **`challenges` table**:
    - Records every challenge, linking a `challenger_id` to an `opponent_id`.
    - Tracks the challenge `timestamp`, `deadline`, resolution status (`resolved`, `resolved_at`), and the final `result` and `score_details`.
- **`completed_challenges_view`**: A pre-built SQL VIEW to simplify querying for past matches, joining the `challenges` and `players` tables.

The database is initialized with a set of players from `initial_players.json`.

## Code & File Structure Summary

- **`app.py`**: The heart of the application. It defines all Flask routes, Socket.IO event handlers, database logic, and business rules for challenges, ranking, and security.
- **`index.html`**: The main user-facing page. It's highly dynamic, with most of its content being rendered and updated by JavaScript based on data received from the backend via Socket.IO.
- **`admin.html`**: The page for admins to manage ongoing matches. It features complex client-side validation for score entry.
- **`db_settings.html`**: The super-admin interface for direct player and database manipulation.
- **`login_tennis.html`**: A visually appealing, animated login page.
- **`schema.sql` / `initial_players.json`**: Define the database structure and its initial data, respectively.
- **`error.html`**: A generic page to display errors.

#### Project Structure
```
stecher_tennis/
├── app.py                     # Main Flask application
├── schema.sql                 # Database schema
├── initial_players.json       # Default player data
├── environment.yml            # Conda environment specification
├── requirements.txt           # Python dependencies (pip)
├── prod-requirements.txt      # Python dependencies for production
├── docker-requirements.txt    # Pinned production dependencies for Docker
├── README.md                  # Project description
├── .env.example               # Environment configuration template
├── backup_tennis_db.sh        # Backup database script
├── check_db.sh                # Script to check database health
├── Dockerfile                 # Multi-stage app container (python:3.12-slim)
├── Dockerfile.caddy           # Custom Caddy build with DuckDNS module
├── docker-compose.yml         # Production stack (pulls from GHCR)
├── docker-compose.build.yml   # Local build override for development
├── Caddyfile                  # Caddy reverse proxy + HTTPS config
├── entrypoint.sh              # Container entrypoint (init_db + gunicorn)
├── build-and-push.sh          # Multi-arch build + GHCR push script
├── deploy.sh                  # RPi deployment/cutover script
├── pytest.ini                 # Test configuration
├── templates/                 # HTML templates
│   ├── login_tennis.html      # Login page
│   ├── index.html             # Main ranking display
│   ├── admin.html             # Admin interface
│   ├── db_settings.html       # Database management
│   └── error.html             # Error pages
├── static/                    # Static assets
│   ├── 01_tennis_racket.png   # Image used within GitHub
│   └── a1_duck_11.png         # Image used within index.html
├── tests/                     # Test suite
│   ├── conftest.py            # Pytest fixtures
│   ├── test_health.py         # Health endpoint tests
│   └── test_db_path.py        # DB_PATH configuration tests
└── tennis.db                  # SQLite database (auto-created)
```

## 🚀 Installation & Setup

### Prerequisites
- Python 3.12+ (or use Miniconda for environment management)
- pip and venv (if not using conda)
- SQLite3

**Recommended**: Miniconda for development, especially on Ubuntu 24.04

### Local Development Setup

#### Option 1: Using Miniconda (Recommended for Development on Ubuntu 24.04)

1. **Setup Project Directory and Conda Environment**
```bash
mkdir stecher_tennis
cd stecher_tennis
git clone <repository-url> .

# Create conda environment from environment.yml
conda env create -f environment.yml

# Activate the environment
conda activate stecher_tennis
```

2. **Verify Installation**
```bash
conda list  # Check installed packages
python --version  # Should show Python 3.12
```

#### Option 2: Using Python venv

1. **Clone and Setup Environment**
```bash
git clone <repository-url>
cd tennis-ranking-app
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install Dependencies**
```bash
pip install -r requirements.txt
```

3. **Environment Configuration**
Create a `.env` file in the project root:
```env
SECRET_KEY=your-secret-key-here
CORS_ALLOWED_ORIGINS=*
FLASK_DEBUG=true
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
```

**Note**: When using conda, all dependencies are managed through `environment.yml`. The environment includes development tools like pytest, black, flake8, and coverage for a complete development experience.

4. **Initialize Database**
```bash
python app.py
```
This will automatically create the SQLite database and populate it with initial players.

5. **Run Development Server**
```bash
python app.py
```

Access the application at `http://127.0.0.1:5000`
Access the application on mobile device use the ip-address from your development server like `http://192.168.1.8:5000`

### Production Requirements

See `docker-requirements.txt` for pinned production dependencies. Core runtime packages:

```
Flask, Flask-SocketIO, Flask-Login, Flask-WTF, flask-cors
gunicorn, eventlet, greenlet
python-engineio, python-socketio
bcrypt, Werkzeug, itsdangerous, Jinja2, click
python-dotenv, pydantic, requests
```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SECRET_KEY` | Flask secret key for sessions | None (required) | Yes |
| `CORS_ALLOWED_ORIGINS` | CORS origins for Socket.IO | `*` | No |
| `FLASK_DEBUG` | Enable debug mode | `false` | No |
| `FLASK_HOST` | Host to bind to | `0.0.0.0` | No |
| `FLASK_PORT` | Port to bind to | `5000` | No |
| `TEST_DATE` | Override current date for testing | None | No |

### Database Configuration

The application uses SQLite with the following key tables:
- `players`: Player information, ranks, availability, and blocking status
- `challenges`: Active and completed challenges with deadlines and results
- `completed_challenges_view`: View for easy access to completed challenges


### 🗄️ Database Schema

The application uses a SQLite database with two main tables: `players` and `challenges`.

#### `players` Table
Stores all user and player information.

```sql
CREATE TABLE players (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    privilege_level TEXT NOT NULL DEFAULT 'player', -- (player, admin, superadmin)
    is_ranked_player INTEGER NOT NULL DEFAULT 1,
    available INTEGER NOT NULL DEFAULT 1,
    rank INTEGER NOT NULL,
    unavailable_since DATETIME,
    unavailability_reason TEXT,
    block_challenger_until DATETIME,
    block_opponent_until DATETIME,
    is_new INTEGER NOT NULL DEFAULT 0
);
```

#### `challenges` Table
Stores all challenge information, both active and completed.

```sql
CREATE TABLE challenges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    challenger_id INTEGER NOT NULL,
    opponent_id INTEGER NOT NULL,
    timestamp DATETIME NOT NULL,
    deadline DATETIME NOT NULL,
    resolved_at DATETIME,
    resolved INTEGER NOT NULL DEFAULT 0,
    result TEXT,
    score_details TEXT,
    scheduled_play_date DATETIME,
    FOREIGN KEY (challenger_id) REFERENCES players(id) ON DELETE CASCADE,
    FOREIGN KEY (opponent_id) REFERENCES players(id) ON DELETE CASCADE
);
```


## 📖 Usage Guide

### Authentication
- All users must log in to access the application.
- Initial credentials are provided in `initial_players.json`. The default password for most users is `DefaultPassword1!`.
- Superadmins can change user passwords via the "DB-Einstellungen" (Database Settings) page.

### User Roles
- **Player**: Can view the ranking pyramid, see active challenges, and manage their own availability. Can issue challenges to eligible opponents.
- **Admin**: Has all player permissions, plus access to the `/admin` page to submit match results.
- **Superadmin**: Has all admin permissions, plus access to the `/db_settings` page to manage players (add, edit, delete, change passwords) and reset the database.

### Main Workflow
1.  **Login**: Access the application with your assigned username and password.
2.  **View Rankings**: The main page displays the ranking pyramid.
3.  **Challenge a Player**:
    - Select yourself from the "Herausforderer" (Challenger) dropdown.
    - The "Gegner" (Opponent) dropdown will populate with eligible players based on ranking rules.
    - Click "Herausfordern" to create the challenge.
4.  **Manage Availability**: Click the small square on your player card in the pyramid to toggle your availability.
5.  **Submit Results (Admins)**: Navigate to the `/admin` page to view pending challenges and submit match scores.
6.  **Manage Players (Superadmins)**: Navigate to the `/db_settings` page to manage the player roster.

### Basic Workflow

1. **Player Management**
   - Players are displayed in a pyramid format based on their ranking
   - Click the availability toggle to make players available/unavailable
   - Ranks 1-10 can challenge anyone above them
   - Ranks 11+ have specific challenge distance limits

2. **Creating Challenges**
   - Select a challenger from the dropdown
   - System automatically shows eligible opponents
   - Submit challenge to create a 10-day deadline
   - Optional: Schedule specific match date/time

3. **Managing Results**
   - Access admin button
   - Enter match results with score validation
   - System automatically updates rankings based on results
   - Players are temporarily blocked after matches

4. **New Player Integration**
   - Use "New Player Challenge" section
   - New player challenges someone in ranks 11-44
   - Successful integration places them in the ranking
   - Failed integration removes them from the system

# 🌐 API Endpoints

## 1. User Authentication & Session Management

These endpoints handle user login, logout, and session control.

### `GET, POST /login`
- **Method:** `GET`, `POST`
- **Description:** Renders the login page (`GET`) and processes user authentication (`POST`). Implements rate limiting to prevent brute-force attacks.
- **Authorization:** Public

### `GET /logout`
- **Method:** `GET`
- **Description:** Logs out the currently authenticated user and redirects to the login page.
- **Authorization:** `@login_required` (Any logged-in user)

### `GET /`
- **Method:** `GET`
- **Description:** The root URL of the application. It automatically redirects to `/login`.
- **Authorization:** Public

---

## 2. Main Application Routes

These routes serve the primary views of the application for authenticated users.

### `GET /index`
- **Method:** `GET`
- **Description:** Displays the main dashboard, including the tennis pyramid, active challenges, completed games, and player status lists.
- **Authorization:** `@login_required`

### `GET /admin`
- **Method:** `GET`
- **Description:** Renders the administration page. This page provides tools for managing active challenges and players. While the route itself only requires login, the actions available on the page are protected by admin-level authorization.
- **Authorization:** `@login_required`

---

## 3. Data-Fetching API Endpoints (JSON)

These endpoints provide data to the frontend for dynamic updates.

### `GET /api/realtime_data`
- **Method:** `GET`
- **Description:** Returns a comprehensive JSON object containing all current data for the application, including players, active/completed challenges, and blocked players. This is the primary endpoint for keeping the UI in sync.
- **Authorization:** `@login_required`

### `GET /get_players`
- **Method:** `GET`
- **Description:** Returns a detailed JSON list of all players, including their rank, availability, and any active blocks.
- **Authorization:** `@login_required`

### `POST /eligible_opponents`
- **Method:** `POST`
- **Description:** Accepts a `challenger_id` and returns a JSON list of opponents that the specified player is currently eligible to challenge based on ranking rules and availability.
- **Authorization:** `@login_required`

---

## 4. Core Action API Endpoints

These endpoints handle the primary user actions within the application.

### `POST /challenge`
- **Method:** `POST`
- **Description:** Creates a new challenge between two players.
- **Authorization:** `@login_required`

### `POST /newplayer_challenge`
- **Method:** `POST`
- **Description:** Adds a new player to the pyramid by immediately creating a challenge against a selected, eligible opponent.
- **Authorization:** `@login_required`

### `POST /toggle_availability`
- **Method:** `POST`
- **Description:** Toggles a player's availability status (e.g., from "available" to "unavailable" for a vacation).
- **Authorization:** `@login_required`

### `POST /update_scheduled_date`
- **Method:** `POST`
- **Description:** Sets or updates the agreed-upon play date and time for an active challenge.
- **Authorization:** `@login_required`

---

## 5. Admin-Only API Endpoints

These endpoints are restricted to users with `admin` or `superadmin` privileges and are used for managing the game and its players.

### `POST /submit_result`
- **Method:** `POST`
- **Description:** Submits the result of a completed challenge. This action resolves the challenge, updates player ranks if necessary, and applies post-game blocks.
- **Authorization:** `@login_required` (Note: The documentation indicates any logged-in user can submit, but it's functionally an admin action performed from the `/admin` page).

### `POST /add_player`
- **Method:** `POST`
- **Description:** Manually adds a new player to the system with a specified name and rank.
- **Authorization:** `@admin_required`

### `POST /update_player`
- **Method:** `POST`
- **Description:** Updates the details (name, rank, etc.) of a specific player. Player ID is passed in the request body as JSON.
- **Authorization:** `@admin_required`

### `POST /delete_player`
- **Method:** `POST`
- **Description:** Deletes a player from the system. Player ID is passed in the request body as JSON.
- **Authorization:** `@admin_required`

### `POST /set_player_block_status`
- **Method:** `POST`
- **Description:** Manually sets or removes a player's block status (challenger, opponent, or none).
- **Authorization:** `@admin_required`

---

## 6. Superadmin-Only Routes

These routes are for system-level database management and are restricted to users with the `superadmin` privilege level.

### `GET /db_settings`
- **Method:** `GET`
- **Description:** Renders the page for database management, including options to back up and restore the database.
- **Authorization:** `@superadmin_required`

### `POST /change_password`
- **Method:** `POST`
- **Description:** Changes a player's password. Player ID and new password are passed in the request body as JSON.
- **Authorization:** `@superadmin_required`

### `POST /reset_completed_challenges_display`
- **Method:** `POST`
- **Description:** Resets the display of completed challenges to zero. All data remains in the database.
- **Authorization:** `@superadmin_required`

### `GET /api/settings/db/export`
- **Method:** `GET`
- **Description:** Downloads a backup of the SQLite database file.
- **Authorization:** `@superadmin_required`

### `POST /api/settings/db/import`
- **Method:** `POST`
- **Description:** Uploads and restores a database file, replacing the current one. Validates schema integrity before applying.
- **Authorization:** `@superadmin_required`

### `POST /reset_database`
- **Method:** `POST`
- **Description:** Resets the entire database to its initial state using `schema.sql` and `initial_players.json`. This action is irreversible.
- **Authorization:** `@superadmin_required`

---

## 🐳 Docker Deployment (Recommended)

The application runs as a Docker Compose stack with two containers:
- **app** — Flask + Gunicorn + eventlet (single worker)
- **caddy** — Custom Caddy build with DuckDNS module for automatic HTTPS via DNS-01 ACME

Both containers are hardened with `read_only` root filesystem, `cap_drop: ALL` (Caddy gets `NET_BIND_SERVICE` back for port binding), and `no-new-privileges` security option.

Pre-built multi-arch images (AMD64 + ARM64) are available on GHCR:
- `ghcr.io/ainxtgendev/stecher-tennis-app:latest`
- `ghcr.io/ainxtgendev/stecher-tennis-caddy:latest`

### Raspberry Pi — Step-by-Step Installation (Clean Install)

#### Prerequisites
- Raspberry Pi 4 or newer
- Raspberry Pi OS **64-bit** (required for ARM64 Docker images)
- Internet connection
- A DuckDNS account with a registered domain (free at [duckdns.org](https://www.duckdns.org))
- Router port forwarding configured (external port 443 → RPi internal port 10443, external port 80 → RPi port 80)

#### Step 1: Install Docker

```bash
# Install Docker using the convenience script
curl -fsSL https://get.docker.com | sh

# Add your user to the docker group (replace 'stecher' with your username)
sudo usermod -aG docker stecher

# Log out and back in for group membership to take effect
exit
```

Log back in via SSH, then verify:
```bash
docker --version
docker compose version
```

#### Step 2: Enable Docker on Boot

```bash
sudo systemctl enable docker
```

#### Step 3: Clone the Repository

```bash
cd ~
git clone -b docker https://github.com/AINxtGenDev/stecher_tennis.git
cd stecher_tennis
```

#### Step 4: Create the Environment File

```bash
cp .env.example .env
nano .env
```

Fill in the **required** values:

| Variable | What to set | Example |
|----------|------------|---------|
| `SECRET_KEY` | Random string for session encryption | Generate with: `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `DUCKDNS_DOMAIN` | Your DuckDNS subdomain (without .duckdns.org) | `nechvatal` |
| `DUCKDNS_TOKEN` | Your DuckDNS API token (36-char UUID) | `f5035eb4-6739-4f5e-b0e7-xxxxxxxxxxxx` |
| `ACME_EMAIL` | Your email for Let's Encrypt | `your-email@gmail.com` |
| `ACME_CA` | Start with staging, switch to production later | `https://acme-staging-v02.api.letsencrypt.org/directory` |
| `CORS_ALLOWED_ORIGINS` | Must match user-facing URL | `https://nechvatal.duckdns.org` |

#### Step 5: Pull and Start the Stack

```bash
docker compose pull
docker compose up -d
```

Wait for the containers to start. Check status:
```bash
docker compose ps
```

Both containers should show `Up` and the app should be `(healthy)`.

#### Step 6: Verify with Staging Certificate

Visit `https://your-domain.duckdns.org` in a browser. You will see a certificate warning (this is expected with staging certs). Accept the warning and verify the app loads correctly.

Check Caddy logs to confirm the staging certificate was obtained:
```bash
docker compose logs caddy | grep "certificate obtained"
```

#### Step 7: Switch to Production Certificate

Once staging works, switch to a real Let's Encrypt certificate:

```bash
# 1. Update ACME_CA in .env
sed -i 's|acme-staging-v02|acme-v02|' .env

# 2. Stop the stack
docker compose down

# 3. Clear cached staging certificates
docker volume rm $(docker volume ls -q | grep caddy_data)

# 4. Start with production certs
docker compose up -d
```

Wait 1-2 minutes for the production certificate to be issued. Then visit `https://your-domain.duckdns.org` — no browser warning this time.

#### Step 8: Verify Everything Works

```bash
# Check containers are running
docker compose ps

# Check Caddy obtained production cert
docker compose logs caddy | grep "certificate obtained"

# Check app health
docker compose exec -T app python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')"
```

Also verify:
- Login works in the browser
- Real-time updates work (open two browser tabs, make a change in one)
- Reboot the RPi (`sudo reboot`) and confirm the app comes back automatically after 1-2 minutes

### Database Location

The SQLite database is stored in a Docker named volume, **not** in the git repository directory:

```
/var/lib/docker/volumes/stecher_tennis_tennis_data/_data/tennis.db
```

This volume persists across `docker compose down` / `up` cycles. The `tennis.db` in `~/stecher_tennis/` is the default from git and is **not** used by the running containers.

To restore a database backup:
```bash
# Stop the app
cd ~/stecher_tennis && docker compose stop app

# Copy backup into the volume
sudo cp /path/to/your/backup.db /var/lib/docker/volumes/stecher_tennis_tennis_data/_data/tennis.db
sudo chown 1000:1000 /var/lib/docker/volumes/stecher_tennis_tennis_data/_data/tennis.db

# Restart the app
docker compose start app
```

### Updating the Deployment

When a new version is available:

```bash
cd ~/stecher_tennis
git pull
docker compose pull
docker compose up -d
```

### Viewing Logs

```bash
# All services
docker compose logs -f

# App only
docker compose logs -f app

# Caddy only
docker compose logs -f caddy
```

### Building Images Locally (Development)

If you want to build images from source instead of pulling from GHCR:

```bash
docker compose -f docker-compose.yml -f docker-compose.build.yml up -d --build
```

### Building and Pushing Multi-Arch Images

To build for both AMD64 and ARM64 and push to GHCR (requires a GitHub PAT with `write:packages` scope):

```bash
export GHCR_TOKEN=ghp_your_token_here
./build-and-push.sh
```

### Network Configuration (Router)

Configure your router to forward these ports to the Raspberry Pi:

| External Port | Internal Port | Protocol | Purpose |
|--------------|---------------|----------|---------|
| 443 | 10443 | TCP | HTTPS (Caddy TLS via Docker) |
| 80 | 80 | TCP | HTTP → HTTPS redirect |

## 🔧 Development

### Development Environment

#### Conda Environment (environment.yml)
The project includes a complete conda environment specification in `environment.yml`:

```yaml
name: stecher_tennis
channels:
  - conda-forge
  - defaults
dependencies:
  # Core dependencies
  - python=3.12
  - flask
  - flask-cors
  - python-dotenv
  - flask-socketio
  - eventlet
  # Development tools
  - pytest
  - black
  - flake8
  - coverage
  - flask-debugtoolbar
  # Production tools
  - gunicorn
  - watchdog
```

#### Development Workflow
```bash
# Activate conda environment
conda activate stecher_tennis

# Start development server with auto-reload
python app.py

# Code formatting
black app.py

# Linting
flake8 app.py

# Run tests
pytest

# Check coverage
coverage run -m pytest
coverage report
```

## ✨ Development Settings

Here are the important development settings:

### Core settings are:
- **.env**: # to enable development mode
  - FLASK_DEBUG=true
- **activate conda environment**: # to enable python environment
  - conda activate stecher_tennis
- **check git status**: # expectation is that there are no changes
  - git status
- **do your development work**
  - code .
  - run tests
- **sync with git**: # sync with github repository https://github.com/AINxtGenDev/stecher_tennis
  - git add .
  - git commit -m "commit message"
  - git push
  - git status

### Testing

The application includes a test date override feature:
```bash
export TEST_DATE="2025-12-31-23-59-59"
python app.py
```

## 🐛 Troubleshooting

### Common Issues

**Socket.IO Connection Problems**
- Ensure `eventlet` is installed and being used as the worker class
- Check CORS configuration in `.env`
- Verify firewall settings allow WebSocket connections

**Database Errors**
- Check SQLite file permissions
- Ensure WAL mode is supported (requires SQLite 3.7.0+)
- Verify foreign key constraints are enabled

**Ranking Calculation Issues**
- The system enforces a maximum of 45 players
- New players start at rank 99 and are re-ranked immediately
- Challenge eligibility is recalculated dynamically

**Performance on Raspberry Pi**
- Use only 1 gunicorn worker with eventlet
- Monitor memory usage with large player counts
- Consider upgrading to Raspberry Pi 4 for better performance

**Docker Container Issues**
- Ensure Docker is installed and the user is in the `docker` group
- Check container status: `docker compose ps`
- Check logs: `docker compose logs -f`
- If Caddy fails to obtain a certificate, verify the `DUCKDNS_TOKEN` is a valid 36-character UUID
- If ACME email is rejected, ensure `ACME_EMAIL` is a real email address (not `example.com`)
- After changing `.env`, restart the stack: `docker compose down && docker compose up -d`
- To clear cached certificates: `docker volume rm $(docker volume ls -q | grep caddy_data)`

**NAT Hairpinning**
- If HTTPS works from external networks (mobile data) but not from the same LAN as the RPi, your router does not support NAT hairpinning. This is a router limitation, not an app issue. Access via the RPi's local IP won't work for HTTPS (certificate is bound to the DuckDNS domain).

### Logs and Monitoring

```bash
# Docker container logs
docker compose logs -f

# App container only
docker compose logs -f app

# Caddy container only
docker compose logs -f caddy

# Container status
docker compose ps
```
## ✨ Total Lines of Code (LOC)

```bash
# app.py                2.654
# index.html              479
# admin.html              227
# db_settings.html        489
# login_tennis.html       494
# stecher_start.html      239
# initial_players.json    112
# schema.sql               67
# error.html               20
#############################
# Total                  4.781
#############################
```

## 📋 Recent Changes

### 2026-06-17 — Critical fixes from code review

Applied the three Critical findings from the standing code review (`REVIEW.md`)
plus one related Warning:

- **CR-01** — Expired challenges are now auto-resolved. `resolve_expired_challenges()`
  was defined but never called, so the 10-day deadline rule was silently never
  enforced. A throttled `@app.before_request` hook (runs at most once per minute)
  now invokes it, working under both `python app.py` and gunicorn.
- **CR-02** — Fixed an operator-precedence/casing bug in the UNIQUE-constraint
  check of `add_player` and `update_player`, so genuine duplicate-name errors are
  detected correctly.
- **CR-03** — `emit_data_update()` in the expired-challenge flow now fires only
  after the transaction commits, so clients never receive rolled-back state.
- **WR-03** — `eventlet.monkey_patch()` is now applied at startup, restoring
  dev/prod parity for cooperative stdlib I/O. Added a smoke test
  (`tests/test_eventlet_patch.py`). Note: `sqlite3`/`bcrypt` are C extensions and
  remain blocking regardless.

## 📝 License

© 2026 Matthias Stecher. All rights reserved.

## 👥 Support

For support or questions:
- **Email**: matthias.stecher@gmx.at
- **Mobile**: +43 664 105 25 56

---
