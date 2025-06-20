# Tennis Ranking Web Application
<img src="static/01_tennis_racket.png" alt="Tennis Racket" width="300">

## Introduction

The **Tennis Ranking Web Application** is a comprehensive system for managing tennis players and organizing challenges between them. Beyond displaying the current ranking list, the application offers real-time dynamic ranking updates, player blocking management, availability tracking, and sophisticated challenge scheduling.

---

## Project Goals

- **Player Management:**  
  Add, edit, and delete players with comprehensive CRUD operations.

- **Challenge Management:**  
  Create, manage, schedule, and evaluate challenges between players with advanced validation.

- **Dynamic Ranking System:**  
  Automatic ranking updates based on match results with sophisticated promotion/demotion rules.

- **Real-time Updates:**  
  Live transmission of changes to all connected clients using Socket.IO.

- **Advanced Scheduling:**  
  Schedule matches with date/time selection and deadline management.

- **Blocking System:**  
  Temporary blocking of players as challengers or opponents after matches.

---

## Technology Stack

- **Backend:**  
  Python with Flask framework ([Flask Documentation](https://flask.palletsprojects.com/en/2.2.x/))

- **Database:**  
  SQLite with WAL mode, initialized via SQL schema ([schema.sql](schema.sql))

- **Real-time Communication:**  
  Flask-SocketIO with eventlet async mode ([Flask-SocketIO Documentation](https://flask-socketio.readthedocs.io/))

- **Frontend:**  
  HTML5, CSS3, JavaScript (jQuery, Bootstrap 5)

- **Additional Components:**  
  JSON data for player initialization ([initial_players.json](initial_players.json))

---

## Architecture & Structure

The application follows a modular architecture with the following core components:

### Core Files

- **app.py** (2,400+ lines):  
  Main Flask server with routing logic, database operations, real-time communication, and comprehensive business logic.

- **HTML Templates:**
  - **index.html:** Main interface with pyramid ranking visualization and challenge forms
  - **admin.html:** Administration interface for managing pending challenges with score validation
  - **db_settings.html:** Player database management interface
  - **error.html:** Error handling page

- **Database:**
  - **schema.sql:** SQL schema with players, challenges tables, and views
  - **initial_players.json:** Initial player data (36 players)

### Key Features

- **Pyramid Visualization:** Players displayed in a 9-row pyramid structure
- **Real-time Updates:** Instant UI updates across all connected clients
- **Advanced Validation:** Comprehensive score validation with tennis rules
- **Responsive Design:** Mobile-optimized interface
- **3D Visual Effects:** Modern UI with hover effects and animations

---

## Main Functionality

### Player Management

- **CRUD Operations:** Full create, read, update, delete functionality
- **Availability Toggle:** Players can mark themselves available/unavailable
- **Blocking System:** Automatic temporary blocking after matches (7 days)
- **New Player Integration:** Add new players directly into challenges (ranks 11-44)
- **Rank Validation:** Maintains 45-player limit with automatic re-ranking

### Challenge System

- **Eligible Opponent Logic:**
  - Ranks 1-10: Can challenge any higher-ranked available player
  - Ranks 11+: Complex range-based challenge rules with unavailability compensation
- **Match Scheduling:** Date and time selection with deadline validation
- **Score Validation:** Tennis-specific score validation (sets, tiebreaks, special results)
- **Result Types:** Win/Loss with scores, forfeit, disqualification, or "didn't happen"

### Real-time Features

- **Socket.IO Integration:** Live updates for all player actions
- **Data Caching:** 10-second TTL cache for performance optimization
- **Event Broadcasting:** Comprehensive event system for UI synchronization

---

## API Endpoints & Routes

### Main Routes
- **/** → **/stecher_start:** Landing page
- **/index:** Main ranking interface
- **/admin:** Challenge administration
- **/db_settings:** Player management interface

### API Endpoints
- **GET /api/realtime_data:** Cached comprehensive data
- **GET /get_players:** All player information
- **POST /eligible_opponents:** Dynamic opponent calculation
- **POST /challenge:** Create new challenge
- **POST /toggle_availability:** Player availability toggle
- **POST /submit_result:** Challenge result submission with validation
- **POST /newplayer_challenge:** New player integration
- **POST /update_scheduled_date:** Match scheduling

### Admin Endpoints
- **POST /add_player:** Add new player
- **POST /update_player:** Edit player details
- **POST /delete_player:** Remove player
- **POST /set_player_block_status:** Manage blocking
- **POST /reset_database:** Full database reset

---

## Database Schema

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
    result TEXT,  -- 'challenger_wins', 'opponent_wins', 'not_happened'
    score_details TEXT,
    scheduled_play_date DATETIME,
    FOREIGN KEY (challenger_id) REFERENCES players(id) ON DELETE CASCADE,
    FOREIGN KEY (opponent_id) REFERENCES players(id) ON DELETE CASCADE
);
```

---

## User Interface Features

### Main Interface (index.html)
- **Pyramid Display:** Visual ranking in 9-row pyramid (1,2,3,4,5,6,7,8,9 players per row)
- **Color-coded Players:**
  - Orange: Available
  - Green: Active challenger
  - Red: Active opponent  
  - Orange with diagonal line: Blocked as opponent
  - Grey with diagonal line: Blocked as challenger
  - White: Unavailable
- **Interactive Elements:** Click-to-toggle availability, challenge forms
- **Collapsible Sections:** Active challenges, blocked players, unavailable players, completed challenges

### Admin Interface (admin.html)
- **Challenge Management:** Pending challenge resolution
- **Score Validation:** Tennis-specific score format validation
- **Result Processing:** Comprehensive result entry with error handling
- **Real-time Updates:** Auto-refresh on changes

### Database Settings (db_settings.html)
- **Player CRUD:** Full player management interface
- **Block Management:** Set/remove player blocks
- **Dangerous Operations:** Database reset with confirmation

---

## Advanced Features

### Score Validation System
- **Set Validation:** Standard sets (6-0 to 6-4, 7-5)
- **Tiebreak Support:** 7-6(x:y) format validation
- **Special Results:** Forfeit, disqualification handling
- **Match Logic:** 2-set wins, 3-set maximum validation

### Real-time Architecture
- **Event System:** Comprehensive Socket.IO event broadcasting
- **Data Synchronization:** All clients receive instant updates
- **Cache Management:** Smart cache invalidation on data changes
- **Connection Management:** Robust reconnection handling

### Responsive Design
- **Mobile Optimization:** Touch-friendly interface
- **Adaptive Layout:** Pyramid scales for different screen sizes
- **Progressive Enhancement:** Fallbacks for older browsers

---

## Security & Configuration

### Security Features
- **Environment Variables:** Configurable secret keys and CORS settings
- **Input Validation:** Comprehensive server-side validation
- **SQL Injection Prevention:** Parameterized queries throughout
- **XSS Protection:** Proper template escaping

### Production Configuration
```python
# Environment Variables
SECRET_KEY=your-production-secret-key
CORS_ALLOWED_ORIGINS=https://your-domain.com
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=false
TEST_DATE=2024-12-01-10-00-00  # Optional: Fixed date for testing
```

---

## NGINX Configuration

WebSocket-ready NGINX configuration for production deployment:

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # Dedicated location for WebSocket /socket.io endpoints
    location /socket.io/ {
        proxy_pass http://127.0.0.1:5000/socket.io/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }

    # Regular HTTP proxy for other routes
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
```

---

## Installation & Setup

### Prerequisites

#### Production Requirements (prod-requirements.txt)
```bash
# Core Flask and Web Server
Flask
gunicorn
Werkzeug
itsdangerous
Jinja2
click

# Flask Plugins
flask-cors
Flask-SocketIO

# Async and Networking
eventlet
greenlet
python-engineio
python-socketio

# Configuration
python-dotenv
```

#### Installation
```bash
# Core dependencies
pip install -r prod-requirements.txt
```

### Quick Development Setup
```bash
# Clone repository
git clone [repository-url]
cd tennis-ranking

# Set environment variables (optional for development)
cp .env.example .env
# Edit .env with your configuration

# Initialize database (automatic on first run)
python app.py

# Access application
# http://localhost:5000
```

### Database Initialization
The application automatically:
1. Creates database schema from `schema.sql`
2. Loads initial players from `initial_players.json` (36 players)
3. Sets up indexes and foreign key constraints
4. Enables WAL mode for better concurrency

### Monitoring & Maintenance

#### Automated Backups
The system includes automated daily database backups:

```bash
# Backup script (backup_tennis_db.sh)
#!/bin/bash
backup_dir="/home/stecher/stecher_tennis/backups"
mkdir -p "$backup_dir"
cp /home/stecher/stecher_tennis/tennis.db "$backup_dir/tennis_$(date +%Y%m%d_%H%M%S).db"

# Keep only last 30 days of backups
find "$backup_dir" -name "tennis_*.db" -mtime +30 -delete
```

```bash
# Crontab entry for daily backup at 4 AM
0 4 * * * /home/stecher/stecher_tennis/backup_tennis_db.sh >/dev/null 2>&1
```

#### Service Monitoring
```bash
# Check service status
sudo systemctl status stecher-tennis.service

# View live logs
sudo journalctl -u stecher-tennis.service -f

# View recent logs
sudo journalctl -u stecher-tennis.service -n 100

# View error logs only
sudo journalctl -u stecher-tennis.service -p err

# View logs for specific time period
sudo journalctl -u stecher-tennis.service --since="2025-06-20 08:00:00"
```

#### File Transfer (for updates)
```bash
# Transfer files to Raspberry Pi
scp -r -o PreferredAuthentications=password . stecher@192.168.1.213:~/stecher_tennis/

# SSH access
ssh stecher@192.168.1.213 -o PreferredAuthentications=password -v
```

---

## Business Logic

### Ranking Rules
- **45 Player Maximum:** Automatic enforcement with re-ranking
- **New Player Integration:** Join at rank 45, challenge up to rank 11-44
- **Challenge Ranges:** Dynamic opponent selection based on rank and availability
- **Blocking System:** 7-day blocks prevent immediate re-challenges

### Challenge Lifecycle
1. **Creation:** Challenger selects eligible opponent
2. **Scheduling:** Optional date/time selection within 10-day deadline
3. **Execution:** Match played by players
4. **Resolution:** Admin enters result with validation
5. **Ranking Update:** Automatic rank adjustments and blocks applied

---

## Performance & Scalability

### Optimization Features
- **Data Caching:** 10-second TTL for frequent queries
- **Database Optimization:** WAL mode, proper indexing
- **Client-side Caching:** Smart UI state preservation
- **Event Debouncing:** Prevents excessive Socket.IO events

### Monitoring
- **Comprehensive Logging:** All operations logged with appropriate levels
- **Error Handling:** Graceful degradation with user feedback
- **Health Checks:** Built-in connection monitoring

---

## Future Enhancements

### Planned Features
- **User Authentication:** Individual player accounts
- **Statistics Dashboard:** Win/loss records, performance metrics
- **Tournament Mode:** Bracket-style competitions
- **Mobile App:** Native iOS/Android applications
- **Advanced Scheduling:** Court booking integration

### Technical Improvements
- **API Rate Limiting:** Prevent abuse
- **Database Migration System:** Version-controlled schema changes
- **Automated Testing:** Unit and integration test suites
- **Performance Monitoring:** Real-time metrics dashboard

---

## Contributing

The application follows modern Python and web development best practices:
- **PEP 8:** Python style guide compliance
- **RESTful API:** Consistent endpoint design
- **Progressive Enhancement:** Graceful fallbacks
- **Accessibility:** ARIA labels and keyboard navigation

---

## License & Credits

© 2025 Matthias Stecher. All rights reserved.

**Contact:**
- Email: matthias.stecher@hpe.com
- Mobile: 0664 105 25 56

**Disclaimer:** No liability for errors or delays in rankings.

## Access URLs

### Development
- Main Interface: `http://localhost:5000/index`
- Admin Panel: `http://localhost:5000/admin`
- Database Settings: `http://localhost:5000/db_settings`
- Landing Page: `http://localhost:5000/stecher_start`

### Production (Example)
- Main Interface: `https://your-domain.duckdns.org:10443/index`
- Admin Panel: `https://your-domain.duckdns.org:10443/admin`
- Database Settings: `https://your-domain.duckdns.org:10443/db_settings`
- Landing Page: `https://your-domain.duckdns.org:10443/stecher_start`

## Troubleshooting

### Common Issues

#### WebSocket Connection Problems
- **Issue**: Socket.IO connection failures or "Invalid session" errors
- **Solution**: Use single eventlet worker in gunicorn configuration
- **Configuration**: `--workers 1 --worker-class eventlet`

#### Database Locks
- **Issue**: Database is locked errors
- **Solution**: WAL mode is enabled automatically, check file permissions
- **Check**: `ls -la tennis.db*` should show proper ownership

#### Service Not Starting
```bash
# Check service logs
sudo journalctl -u stecher-tennis.service -n 50

# Check if port is in use
sudo netstat -tlnp | grep :8000

# Restart service
sudo systemctl restart stecher-tennis.service
```

#### SSL Certificate Issues (Caddy)
```bash
# Check Caddy logs
sudo journalctl -u caddy -n 50

# Test Caddy configuration
sudo caddy fmt --overwrite /etc/caddy/Caddyfile
sudo caddy validate --config /etc/caddy/Caddyfile
```

#### Memory Issues on Raspberry Pi
- Monitor with: `htop` or `free -h`
- Adjust `MemoryMax=2G` in systemd service if needed
- Consider reducing cache TTL if memory is limited

---

## Technical Resources

- **Flask Documentation:** [https://flask.palletsprojects.com/](https://flask.palletsprojects.com/)
- **Flask-SocketIO:** [https://flask-socketio.readthedocs.io/](https://flask-socketio.readthedocs.io/)
- **Bootstrap 5:** [https://getbootstrap.com/](https://getbootstrap.com/)
- **Socket.IO:** [https://socket.io/](https://socket.io/)
- **Caddy Server:** [https://caddyserver.com/](https://caddyserver.com/)
- **DuckDNS:** [https://www.duckdns.org/](https://www.duckdns.org/)

- **Flask Documentation:** [https://flask.palletsprojects.com/](https://flask.palletsprojects.com/)
- **Flask-SocketIO:** [https://flask-socketio.readthedocs.io/](https://flask-socketio.readthedocs.io/)
- **Bootstrap 5:** [https://getbootstrap.com/](https://getbootstrap.com/)
- **Socket.IO:** [https://socket.io/](https://socket.io/)

---

**Version:** 2.08-prod-final  
**Last Updated:** June 20, 2025
