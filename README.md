# Tennis Ranking Web Application

<img src="static/01_tennis_racket.png" alt="Tennis Racket" width="300">

A comprehensive web-based tennis ranking management system with real-time updates, challenge management, and sophisticated player tracking.

## 🎯 Project Overview

The **Tennis Ranking Web Application** is a full-featured system for managing tennis players in a ranking-based tournament format. It provides real-time dynamic ranking updates, player blocking management, availability tracking, and advanced challenge scheduling with automatic rank adjustments based on match results.

## ✨ Key Features

### Player Management
- **Dynamic Ranking System**: Automatic ranking updates based on match results
- **Player CRUD Operations**: Add, edit, and delete players with comprehensive validation
- **Availability Tracking**: Players can toggle their availability status
- **Blocking System**: Temporary blocking of players as challengers or opponents after matches
- **New Player Integration**: Special workflow for integrating new players into the ranking

### Challenge Management
- **Challenge Creation**: Players can challenge opponents within specific ranking rules
- **Eligibility Rules**: Sophisticated rules determining valid opponents based on rank
- **Schedule Management**: Set specific dates and times for matches
- **Deadline Tracking**: Automatic deadline management with 10-day challenge windows
- **Result Processing**: Comprehensive result entry with score validation

### Real-time Features
- **Live Updates**: Socket.IO-powered real-time updates across all connected clients
- **Dynamic UI**: Instant reflection of changes without page refreshes
- **Multi-client Sync**: All users see updates simultaneously

### Advanced UI
- **Pyramid Display**: Visual pyramid representation of the ranking hierarchy
- **Color-coded Status**: Different colors for available, unavailable, active challengers/opponents, and blocked players
- **Responsive Design**: Mobile-optimized interface with touch-friendly controls
- **3D Effects**: Modern visual enhancements for better user experience

## 🛠 Technical Stack

### Backend
- **Framework**: Flask (Python web framework)
- **Real-time**: Flask-SocketIO with eventlet for WebSocket support
- **Database**: SQLite with comprehensive schema and views
- **Configuration**: python-dotenv for environment management
- **Validation**: Custom business logic validation for tennis match rules

### Frontend
- **UI Framework**: Bootstrap 5 for responsive design
- **Real-time Client**: Socket.IO client for live updates
- **Styling**: Custom CSS with 3D effects and animations
- **JavaScript**: jQuery for DOM manipulation and AJAX requests

### Deployment
- **Web Server**: Gunicorn with eventlet workers
- **Reverse Proxy**: Caddy for HTTPS termination and static file serving
- **SSL**: Automatic Let's Encrypt certificate management
- **Platform**: Optimized for Raspberry Pi deployment

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

Access the application at `http://localhost:5000`

### Production Requirements
```
Flask==2.3.2
gunicorn==21.2.0
Flask-SocketIO==5.3.4
eventlet==0.33.3
python-dotenv==1.0.0
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

## 📖 Usage Guide

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
   - Access admin panel at `/admin`
   - Enter match results with score validation
   - System automatically updates rankings based on results
   - Players are temporarily blocked after matches

4. **New Player Integration**
   - Use "New Player Challenge" section
   - New player challenges someone in ranks 11-44
   - Successful integration places them in the ranking
   - Failed integration removes them from the system

### Admin Functions

Access admin features at:
- `/admin` - Challenge result management
- `/db_settings` - Player management and database operations

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

## 🗄️ Database Schema

### Players Table
```sql
CREATE TABLE players (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    available INTEGER NOT NULL DEFAULT 1,
    rank INTEGER NOT NULL,
    unavailable_since DATETIME,
    block_challenger_until DATETIME,
    block_opponent_until DATETIME,
    is_new INTEGER NOT NULL DEFAULT 0
);
```

### Challenges Table
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

### Project Structure
```
tennis-ranking-app/
├── app.py                 # Main Flask application
├── schema.sql            # Database schema
├── initial_players.json  # Default player data
├── environment.yml       # Conda environment specification
├── requirements.txt      # Python dependencies (pip)
├── .env                  # Environment configuration
├── templates/            # HTML templates
│   ├── index.html       # Main ranking display
│   ├── admin.html       # Admin interface
│   ├── db_settings.html # Database management
│   └── error.html       # Error pages
├── static/              # Static assets
│   └── images/
└── tennis.db           # SQLite database (auto-created)
```

### Key Components

1. **Real-time Data Flow**
   - Client connects via Socket.IO
   - Server emits `data_update` events on any change
   - Clients automatically refresh UI with new data

2. **Challenge Rules Engine**
   - Rank-based opponent eligibility calculation
   - Automatic rank adjustment after matches
   - Temporary blocking system to prevent immediate re-challenges

3. **Caching Layer**
   - 10-second TTL cache for frequently accessed data
   - Thread-safe cache invalidation on updates
   - Improved performance for multiple concurrent users

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
- **Mobile**: 0664 105 25 56

---

## 📊 Tennis Ranking Project - Code Line Count

Here's the complete breakdown of code lines in your tennis ranking project:

### Core Application Files
- **app.py**: 1,444 lines (Main Flask application with all backend logic)
- **initial_players.json**: 40 lines (Initial player data)
- **schema.sql**: 56 lines (Database schema)
- **environment.yml**: 24 lines (Conda environment specification)

### HTML Template Files
- **admin.html**: 485 lines (Administration interface with extensive CSS/JS)
- **db_settings.html**: 380 lines (Database management interface)
- **index.html**: 772 lines (Main interface with pyramid visualization)
- **error.html**: 21 lines (Simple error page)

### Project Summary
- **Total Lines**: 3,222
- **By Category**:
  - Core files (Python/JSON/SQL/YAML): 1,564 lines
  - HTML templates: 1,658 lines
- **By Technology**:
  - Python (Flask/Backend): 1,444 lines (44.8%)
  - HTML/CSS/JavaScript: 1,658 lines (51.4%)
  - SQL (Database Schema): 56 lines (1.7%)
  - JSON (Initial Data): 40 lines (1.2%)
  - YAML (Environment Config): 24 lines (0.7%)

This is a substantial project with over 3,200 lines of code! The distribution shows it's well-balanced between backend logic (Python) and frontend presentation (HTML/CSS/JavaScript), which makes sense for a full-stack web application with rich user interfaces like your pyramid visualization and real-time updates. The project includes comprehensive development tooling through conda environment management.

---

**Version**: 2.09-prod-opt  
**Last Updated**: June 20, 2025

---

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
