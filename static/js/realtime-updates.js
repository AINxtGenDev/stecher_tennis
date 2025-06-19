// Optimized JavaScript for real-time updates
$(document).ready(function () {
    // === STATE MANAGEMENT ===
    let appState = {
        players: [],
        active_challenges: [],
        completed_challenges: [],
        blocked_challenger_players: [],
        blocked_opponent_players: [],
        unavailable_players: [],
        lastUpdate: null
    };

    // Temporary selection state
    let tempSelections = {
        challengerId: null,
        opponentId: null,
        newPlayerOpponentId: null
    };

    // === UTILITY FUNCTIONS ===
    function formatDateTime(dateStr) {
        if (!dateStr) return 'N/A';
        try {
            const dt = new Date(dateStr);
            return dt.toLocaleString('de-DE', {
                year: 'numeric', month: '2-digit', day: '2-digit',
                hour: '2-digit', minute: '2-digit'
            });
        } catch (e) {
            return dateStr;
        }
    }

    function showNotification(message, type = 'info', duration = 5000) {
        const $result = $('#challengeResult');
        $result.removeClass('alert-success alert-danger alert-info alert-warning')
               .addClass(`alert-${type}`)
               .html(message)
               .fadeIn();
        
        if (duration > 0) {
            setTimeout(() => $result.fadeOut(), duration);
        }
    }

    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // === DOM UPDATE FUNCTIONS ===
    function updatePlayerPyramid(players) {
        players.forEach(player => {
            const $playerDiv = $(`#player-${player.id}`);
            if (!$playerDiv.length) return;

            // Update text content
            $playerDiv.find('.player-info').html(`Rang ${player.rank}<br>${player.name}`);

            // Update availability toggle
            const $toggle = $playerDiv.find('.availability-toggle');
            $toggle.toggleClass('available', player.available);

            // Reset all style classes
            $playerDiv.removeClass('unavailable challenger opponent blocked blocked-loser');

            // Apply appropriate styling based on status
            if (!player.available) {
                $playerDiv.addClass('unavailable');
            } else if (player.blocked_opponent) {
                $playerDiv.addClass('blocked');
            } else if (player.blocked_challenger) {
                $playerDiv.addClass('blocked-loser');
            }
        });

        // Apply active challenge colors
        applyActiveChallengersColors();
        applyTemporarySelections();
    }

    function updateActiveChallenges(challenges) {
        const $container = $('#active-challenges-list');
        
        if (!challenges || challenges.length === 0) {
            $container.html('<p>Derzeit keine aktiven Herausforderungen.</p>');
            $('#activeChallengesHeader .badge-count').text('0');
            return;
        }

        let html = '';
        challenges.forEach(challenge => {
            // Generate valid play dates
            const validDates = generateValidPlayDates(challenge.deadline);
            
            html += `
                <div class="challenge-entry"
                     data-challenge-id="${challenge.id}"
                     data-challenger-id="${challenge.challenger_id}"
                     data-opponent-id="${challenge.opponent_id}"
                     data-deadline="${challenge.deadline || ''}"
                     data-scheduled-date="${challenge.scheduled_play_date || ''}">
                    <span class="challenge-names">
                        <span class="challenger-name-color">${challenge.challenger_name}</span>
                        gegen
                        <span class="opponent-name-color">${challenge.opponent_name}</span>
                    </span>
                    <div class="challenge-date-selector">
                        <select class="form-select form-select-sm scheduled-date-dropdown ${challenge.scheduled_play_date ? 'has-selection' : ''}">
                            <option value="">Datum wählen...</option>
                            ${validDates.map(date => 
                                `<option value="${date}" ${challenge.scheduled_play_date === date ? 'selected' : ''}>${date}</option>`
                            ).join('')}
                        </select>
                    </div>
                    <span class="challenge-deadline">Frist: ${challenge.deadline_formatted || 'N/A'}</span>
                </div>
            `;
        });

        $container.html(html);
        $('#activeChallengesHeader .badge-count').text(challenges.length);
        
        // Update challenge storage for coloring
        saveChallenges(challenges.map(c => ({
            challenger_id: c.challenger_id,
            opponent_id: c.opponent_id
        })));
    }

    function generateValidPlayDates(deadlineStr) {
        if (!deadlineStr) return [];
        
        const now = new Date();
        const deadline = new Date(deadlineStr);
        const dates = [];
        
        const current = new Date(now);
        current.setHours(0, 0, 0, 0);
        
        while (current <= deadline) {
            dates.push(current.toISOString().split('T')[0]);
            current.setDate(current.getDate() + 1);
        }
        
        return dates;
    }

    function updateCompletedChallenges(challenges) {
        const $container = $('#completed-challenges-list');
        
        if (!challenges || challenges.length === 0) {
            $container.html('<p>Bisher keine durchgeführten Herausforderungen.</p>');
            $('#completedChallengesHeader .badge-count').text('0');
            return;
        }

        let html = '';
        challenges.forEach(challenge => {
            let resultText = 'Unbekannt';
            let resultClass = '';
            
            if (challenge.result === 'challenger_wins') {
                resultText = `${challenge.challenger_name} gewann`;
                resultClass = 'result-challenger-wins';
                if (challenge.score_details) {
                    resultText += `: ${challenge.score_details}`;
                }
            } else if (challenge.result === 'opponent_wins') {
                resultText = `${challenge.opponent_name} gewann`;
                resultClass = 'result-opponent-wins';
                if (challenge.score_details) {
                    resultText += `: ${challenge.score_details}`;
                }
            } else if (challenge.result === 'not_happened') {
                resultText = 'Nicht stattgefunden';
                resultClass = 'result-not-happened';
            }

            html += `
                <div class="completed-entry">
                    <span class="completed-names">${challenge.challenger_name} gegen ${challenge.opponent_name}</span>
                    <span class="completed-result ${resultClass}">${resultText}</span>
                    <span class="completed-info">(${challenge.resolved_at_formatted || 'N/A'})</span>
                </div>
            `;
        });

        $container.html(html);
        $('#completedChallengesHeader .badge-count').text(challenges.length);
    }

    function updateBlockedPlayers(challengerPlayers, opponentPlayers) {
        const $container = $('#blocked-players-list');
        
        let html = '<strong>Gesperrte Herausforderer:</strong>';
        if (challengerPlayers && challengerPlayers.length > 0) {
            challengerPlayers.forEach(player => {
                html += `
                    <div class="blocked-entry">
                        <span class="blocked-name">${player.name}</span>
                        <span class="blocked-info">- gesperrt bis: ${player.block_challenger_until_formatted || 'N/A'}</span>
                    </div>
                `;
            });
        } else {
            html += '<p style="margin-left: 15px; font-style: italic;">Keine.</p>';
        }

        html += '<br><strong>Gesperrte Gegner:</strong>';
        if (opponentPlayers && opponentPlayers.length > 0) {
            opponentPlayers.forEach(player => {
                html += `
                    <div class="blocked-entry">
                        <span class="blocked-name">${player.name}</span>
                        <span class="blocked-info">- gesperrt bis: ${player.block_opponent_until_formatted || 'N/A'}</span>
                    </div>
                `;
            });
        } else {
            html += '<p style="margin-left: 15px; font-style: italic;">Keine.</p>';
        }

        $container.html(html);
        
        // Update badge count (unique blocked players)
        const uniqueBlockedIds = new Set();
        [...(challengerPlayers || []), ...(opponentPlayers || [])].forEach(p => uniqueBlockedIds.add(p.id));
        $('#blockedPlayersHeader .badge-count').text(uniqueBlockedIds.size);
    }

    function updateUnavailablePlayers(players) {
        const $container = $('#unavailable-players-list');
        
        if (!players || players.length === 0) {
            $container.html('<p>Alle Spieler sind derzeit verfügbar.</p>');
            $('#unavailablePlayersHeader .badge-count').text('0');
            return;
        }

        let html = '';
        players.forEach(player => {
            html += `
                <div class="unavailable-entry">
                    <span class="unavailable-name">${player.name}</span>
                    <span class="unavailable-info">nicht verfügbar seit: ${player.unavailable_since_formatted || 'N/A'}</span>
                </div>
            `;
        });

        $container.html(html);
        $('#unavailablePlayersHeader .badge-count').text(players.length);
    }

    function updateDropdowns() {
        // Update challenger dropdown
        const $challengerSelect = $('#challenger');
        const currentChallenger = $challengerSelect.val();
        $challengerSelect.html('<option value="">Wählen Sie einen Herausforderer...</option>');

        appState.players.forEach(player => {
            if (player.available && !player.in_challenge && !player.blocked_challenger) {
                const option = `<option value="${player.id}" class="challenger-option">${player.name} (Rang ${player.rank})</option>`;
                $challengerSelect.append(option);
            }
        });

        // Restore selection if still valid
        if (currentChallenger && $challengerSelect.find(`option[value="${currentChallenger}"]`).length) {
            $challengerSelect.val(currentChallenger);
        }

        // Update new player opponent dropdown
        const $newPlayerOpponentSelect = $('#newplayer-opponent');
        const currentNewPlayerOpponent = $newPlayerOpponentSelect.val();
        $newPlayerOpponentSelect.html('<option value="">Bitte auswählen...</option>');

        appState.players
            .filter(p => p.rank >= 11 && p.rank <= 35 && p.available && !p.in_challenge && !p.blocked_opponent)
            .forEach(player => {
                const option = `<option value="${player.id}" class="opponent-option">${player.name} (Rang ${player.rank})</option>`;
                $newPlayerOpponentSelect.append(option);
            });

        // Restore selection if still valid
        if (currentNewPlayerOpponent && $newPlayerOpponentSelect.find(`option[value="${currentNewPlayerOpponent}"]`).length) {
            $newPlayerOpponentSelect.val(currentNewPlayerOpponent);
        }
    }

    // === CHALLENGE COLORING FUNCTIONS ===
    const CHALLENGES_KEY = 'tennis_challenges';

    function saveChallenges(challenges) {
        try {
            localStorage.setItem(CHALLENGES_KEY, JSON.stringify(challenges));
        } catch (e) {
            console.error("Error saving challenges to localStorage:", e);
        }
    }

    function getChallenges() {
        try {
            const challenges = localStorage.getItem(CHALLENGES_KEY);
            return challenges ? JSON.parse(challenges) : [];
        } catch (e) {
            console.error("Error reading challenges from localStorage:", e);
            return [];
        }
    }

    function applyActiveChallengersColors() {
        $('.player').removeClass('challenger opponent');
        
        const challenges = getChallenges();
        challenges.forEach(challenge => {
            const $challenger = $(`#player-${challenge.challenger_id}`);
            const $opponent = $(`#player-${challenge.opponent_id}`);
            
            if ($challenger.length && !$challenger.hasClass('unavailable') && 
                !$challenger.hasClass('blocked') && !$challenger.hasClass('blocked-loser')) {
                $challenger.addClass('challenger');
            }
            
            if ($opponent.length && !$opponent.hasClass('unavailable') && 
                !$opponent.hasClass('blocked') && !$opponent.hasClass('blocked-loser')) {
                $opponent.addClass('opponent');
            }
        });
    }

    function applyTemporarySelections() {
        const applyHighlight = (playerId, className) => {
            if (!playerId) return;
            const $player = $(`#player-${playerId}`);
            if ($player.length && !$player.hasClass('unavailable') && 
                !$player.hasClass('blocked') && !$player.hasClass('blocked-loser')) {
                if (className === 'challenger') $player.removeClass('opponent');
                if (className === 'opponent') $player.removeClass('challenger');
                $player.addClass(className);
            }
        };

        applyHighlight(tempSelections.challengerId, "challenger");
        applyHighlight(tempSelections.opponentId, "opponent");
        applyHighlight(tempSelections.newPlayerOpponentId, "opponent");
    }

    // === SOCKET.IO SETUP ===
    const socket = io({
        reconnectionAttempts: 5,
        reconnectionDelay: 2000,
        timeout: 10000
    });

    // Connection event handlers
    socket.on("connect", function() {
        console.log("Socket.IO connected:", socket.id);
        showNotification("Verbindung hergestellt", "success", 2000);
        
        // Request full update on connect/reconnect
        socket.emit("request_full_update");
    });

    socket.on("disconnect", function(reason) {
        console.log("Socket.IO disconnected:", reason);
        showNotification("Verbindung unterbrochen - versuche erneut...", "warning", 0);
    });

    socket.on("connect_error", (err) => {
        console.error("Socket.IO connection error:", err.message);
        showNotification("Verbindungsfehler zum Server", "danger", 0);
    });

    socket.on("connection_ack", function(data) {
        console.log("Connection acknowledged:", data);
    });

    // === OPTIMIZED DATA UPDATE HANDLERS ===
    socket.on("data_update", function(response) {
        console.log("Received data_update:", response.type);
        
        if (response.data) {
            // Update application state
            appState = { ...appState, ...response.data };
            appState.lastUpdate = new Date().toISOString();
            
            // Update UI components efficiently
            updatePlayerPyramid(appState.players);
            updateActiveChallenges(appState.active_challenges);
            updateCompletedChallenges(appState.completed_challenges);
            updateBlockedPlayers(appState.blocked_challenger_players, appState.blocked_opponent_players);
            updateUnavailablePlayers(appState.unavailable_players);
            updateDropdowns();
            
            // Hide any connection warnings
            if ($('#challengeResult').hasClass('alert-warning') || $('#challengeResult').hasClass('alert-danger')) {
                $('#challengeResult').fadeOut();
            }
        }
    });

    socket.on("player_update", function(data) {
        console.log("Received player_update:", data.action, data.player?.id);
        
        if (data.player) {
            // Update specific player in state
            const playerIndex = appState.players.findIndex(p => p.id === data.player.id);
            if (playerIndex !== -1) {
                appState.players[playerIndex] = data.player;
                updatePlayerPyramid([data.player]);
                updateDropdowns();
            }
        }
    });

    socket.on("challenge_update", function(data) {
        console.log("Received challenge_update:", data.action, data.challenge_id);
        // Request full update for challenges as they affect multiple UI components
        socket.emit("request_full_update");
    });

    socket.on("scheduled_date_update", function(data) {
        console.log("Received scheduled_date_update:", data.challenge_id, data.scheduled_date);
        
        // Update specific challenge entry
        const $entry = $(`.challenge-entry[data-challenge-id="${data.challenge_id}"]`);
        if ($entry.length) {
            const $dropdown = $entry.find('.scheduled-date-dropdown');
            if (data.scheduled_date) {
                $dropdown.val(data.scheduled_date).addClass('has-selection');
            } else {
                $dropdown.val('').removeClass('has-selection');
            }
        }
    });

    socket.on("database_reset", function(data) {
        console.log("Received database_reset event:", data);
        showNotification("Die Datenbank wurde zurückgesetzt. Lade neue Daten...", "info", 3000);
        setTimeout(() => socket.emit("request_full_update"), 1000);
    });

    // Periodic ping to check connection health
    let missedPongs = 0;
    const maxMissedPongs = 3;
    
    const pingInterval = setInterval(() => {
        if (socket.connected) {
            socket.emit('ping');
            
            const pongTimeout = setTimeout(() => {
                missedPongs++;
                console.warn(`Missed pong ${missedPongs}/${maxMissedPongs}`);
                
                if (missedPongs >= maxMissedPongs) {
                    console.error('Connection appears to be stale, forcing reconnect');
                    socket.disconnect();
                    socket.connect();
                    missedPongs = 0;
                }
            }, 5000); // 5 second timeout for pong
            
            socket.once('pong', () => {
                clearTimeout(pongTimeout);
                missedPongs = 0;
            });
        }
    }, 15000); // Ping every 15 seconds

    // === FALLBACK: Periodic data fetch (in case SocketIO fails) ===
    const periodicUpdate = debounce(() => {
        if (!socket.connected) {
            console.log("Socket disconnected, using fallback data fetch");
            fetch('/api/realtime_data')
                .then(response => response.json())
                .then(result => {
                    if (result.success && result.data) {
                        // Update state directly
                        appState = { ...appState, ...result.data };
                        updatePlayerPyramid(appState.players);
                        updateActiveChallenges(appState.active_challenges);
                        updateCompletedChallenges(appState.completed_challenges);
                        updateBlockedPlayers(appState.blocked_challenger_players, appState.blocked_opponent_players);
                        updateUnavailablePlayers(appState.unavailable_players);
                        updateDropdowns();
                    }
                })
                .catch(error => console.error("Fallback data fetch error:", error));
        }
    }, 5000);

    // Use fallback every 2 minutes if disconnected
    setInterval(periodicUpdate, 120000);

    // Export functions for use by existing code
    window.tennisApp = {
        tempSelections,
        showNotification,
        applyTemporarySelections,
        socket
    };
});
