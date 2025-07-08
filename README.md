# Tennis Ranking Web Application

<img src="static/01_tennis_racket.png" alt="Tennis Racket" width="300">

A comprehensive web-based tennis ranking management system with real-time updates, challenge management, and sophisticated player tracking.

## 🎯 Project Overview

The **Tennis Ranking Web Application** is a full-featured system for managing tennis players in a ranking-based tournament format. It provides real-time dynamic ranking updates, player blocking management, availability tracking, and advanced challenge scheduling with automatic rank adjustments based on match results.
This version (v3.xx) introduces a robust authentication and authorization system, enhancing security and providing role-based access control for players, administrators, and super-administrators.

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

## 4. Data Model (`schema.sql`)

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
tennis-ranking-app/
├── app.py                   # Main Flask application
├── schema.sql               # Database schema
├── initial_players.json     # Default player data
├── environment.yml          # Conda environment specification
├── requirements.txt         # Python dependencies (pip)
├── prod-requirements.txt    # Python dependencies for production
├── README.md                # Project description
├── .env                     # Environment configuration
├── backup_tennis _db.sh     # backup database script
├── check_db.sh              # script to check database healthy
├── templates/               # HTML templates
│   ├── login_tennis.html    # Login page
│   ├── index.html           # Main ranking display
│   ├── admin.html           # Admin interface
│   ├── db_settings.html     # Database management
│   └── error.html           # Error pages
├── static/                  # Static assets
│   ├── 01_tennis_racket.png # image used withih github
│   └── a1_duck_11.png       # image used within index.html
└── tennis.db                # SQLite database (auto-created)
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

### Production Requirements
```
# Core Flask and Web Server
Flask
gunicorn
bcrypt
Werkzeug
itsdangerous
Jinja2
click
pip

# Flask Plugins
flask-cors
Flask-SocketIO
Flask-Login
Flask-WTF

# Async and Networking
eventlet
greenlet
python-engineio
python-socketio

# Configuration
python-dotenv

# Other potential runtime dependencies (include ONLY if your app uses them in production)
google-generativeai
openai
numpy
scipy
pydantic
requests
```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SECRET_KEY` | Flask secret key for sessions | `default-dev-key-for-testing-only` | Yes (production) |
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

## 🌐 API Endpoints

### Player Management
- `GET /get_players` - Retrieve all players with status
- `POST /toggle_availability` - Toggle player availability
- `POST /eligible_opponents` - Get valid opponents for a challenger

### Challenge Management
- `POST /challenge` - Create new challenge
- `POST /submit_result` - Submit match result (admin only)
- `POST /update_scheduled_date` - Update match scheduling
- `POST /newplayer_challenge` - Create challenge for new player

### Admin Operations
- `POST /add_player` - Add new player (admin)
- `POST /update_player` - Update player details (admin)
- `POST /delete_player` - Remove player (admin)
- `POST /set_player_block_status` - Manage player blocking (admin)
- `POST /reset_database` - Reset entire database (admin)

### Data Access
- `GET /api/realtime_data` - Get current system state
- `GET /admin` - Admin interface for challenge management
- `GET /db_settings` - Database management interface


## 🐧 Raspberry Pi Deployment

### System Requirements
- Raspberry Pi 4 or newer
- Raspberry Pi OS (64-bit)
- Internet connection for SSL certificates

### Production Deployment

1. **System Setup**
```bash
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install python3-pip python3-venv libatlas-base-dev libsqlite3-dev -y
```

2. **Application Setup**
```bash
cd /home/pi
python3 -m venv tennis_app
cd tennis_app
source bin/activate
pip install -r requirements.txt
```

3. **Environment Configuration**
```bash
sudo nano /home/pi/tennis_app/.env
```
```env
SECRET_KEY=your-production-secret-key
CORS_ALLOWED_ORIGINS=https://your-domain.com:10443
```

4. **Systemd Service**
```bash
sudo nano /etc/systemd/system/tennis-app.service
```
```ini
[Unit]
Description=Tennis Ranking Application
After=network.target

[Service]
User=pi
Group=www-data
WorkingDirectory=/home/pi/tennis_app
EnvironmentFile=/home/pi/tennis_app/.env
ExecStart=/home/pi/tennis_app/bin/gunicorn --workers 1 --worker-class eventlet --bind 127.0.0.1:8000 --timeout 120 app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

5. **Caddy Reverse Proxy**
```bash
# Install Caddy
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install caddy

# Configure Caddy
sudo nano /etc/caddy/Caddyfile
```
```caddy
your-domain.com {
    tls your-email@example.com
    reverse_proxy localhost:8000 {
        header_up Host {http.request.host}
        header_up X-Real-IP {http.request.remote}
        header_up X-Forwarded-For {http.request.remote}
        header_up X-Forwarded-Proto {http.request.scheme}
    }
}
```

6. **Start Services**
```bash
sudo systemctl daemon-reload
sudo systemctl enable tennis-app.service caddy
sudo systemctl start tennis-app.service caddy
```

### Network Configuration
Configure your router to forward port 443 (HTTPS) to your Raspberry Pi for external access.

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

### Logs and Monitoring

```bash
# Service logs
sudo journalctl -u tennis-app.service -f

# Caddy logs
sudo journalctl -u caddy -f

# Application logs
tail -f /var/log/caddy/access.log
```

## 📝 License

© 2025 Matthias Stecher. All rights reserved.

## 👥 Support

For support or questions:
- **Email**: matthias.stecher@hpe.com
- **Mobile**: 0043 664 105 25 56

---
