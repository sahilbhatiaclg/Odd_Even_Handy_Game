# Odd-Even Hand Cricket

A starter web project for a private, two-player online hand-cricket game. It uses Python, Flask, Flask-SocketIO, HTML, CSS and vanilla JavaScript.

> This is an early playable foundation, not a production-ready multiplayer service. Read the limitations and TODO list before deploying it publicly.

## 1. Game concept

Two players create or join a private room and play hand cricket in a browser.

The match has three main stages:

1. Toss
2. First innings
3. Second innings

### Toss rules

- Each player is assigned Odd or Even. In this starter, the room creator chooses their side and the joining player automatically receives the opposite side.
- Both players choose a number from 1 to 6.
- The sum of the two numbers is calculated when the timer expires.
- An even sum means the Even player wins; an odd sum means the Odd player wins.
- The toss winner chooses whether to bat or bowl first.

### Number selection and timer (latest agreed rule)

- Each round has a server-controlled countdown.
- Both players may change their selected number as many times as they want before the deadline.
- Clicking a number does **not** submit or lock it.
- The server stores each player's latest selection.
- When the server timer expires, the latest selections are captured and revealed together.
- The opponent must not receive the other player's current selection before the reveal.
- The same selection mechanism is used for the toss and every ball in both innings.

The client displays a countdown for convenience, but the server deadline is authoritative.

### Batting rules

- Both players select numbers from 1 to 6.
- If the batsman's number equals the bowler's number, the batsman is OUT.
- If the numbers differ, the batsman's selected number is added to their score.
- Balls continue until the batsman is OUT.

### Second innings and target

- After the first batsman is OUT, the players switch roles.
- The second innings target is the first innings score plus one.
- The second batsman wins by reaching the target.
- If the second batsman gets OUT before reaching the target, the first-innings player wins.

## 2. Timeout policy in this starter

The detailed timeout policy has not yet been confirmed. The starter currently uses a simple default:

- If either player has not selected a number when the timer expires, the round ends and the match is marked as a timeout.
- This is intentionally isolated in `game/engine.py` so it can be replaced with a grace-period/reconnection/forfeit policy.

Recommended final policy: pause the match, allow a short reconnection grace period, then forfeit if the missing player does not return.

## 3. Technology stack

| Layer | Technology | Responsibility |
|---|---|---|
| Frontend | HTML, CSS, JavaScript | Screens, buttons, scoreboard and timer display |
| Backend | Python + Flask | Website routes and server setup |
| Real-time | Flask-SocketIO | Room events and live updates |
| Game logic | Python | Toss, innings, score and winner calculation |
| Active room state | Python memory | Temporary room and match data |
| Persistent data (later) | SQLite | Match history and statistics |
| Version control | Git + GitHub | Source history and collaboration |

C or C++ is not required for this project. The important challenge is real-time web communication, not low-level computation.

## 4. Project structure

```text
odd-even-hand-cricket/
│
├── app.py                  # Flask app and Socket.IO event handlers
├── requirements.txt        # Python dependencies
├── README.md               # Project guide, logic and roadmap
├── .gitignore
│
├── game/
│   ├── __init__.py
│   └── engine.py            # Game phases, toss, innings and scoring
│
├── rooms/
│   ├── __init__.py
│   └── room_manager.py      # Create rooms and add players
│
├── templates/
│   ├── index.html           # Create/join room page
│   └── game.html            # Match screen
│
├── static/
│   ├── css/
│   │   └── style.css        # Website styling
│   └── js/
│       ├── main.js          # Home page events
│       └── game.js          # Match UI and Socket.IO client
│
└── tests/                   # Add automated tests here
```

## 5. Run locally

### Requirements

- Python 3.10 or newer
- pip
- A modern browser
- Git (optional, for version control)

### Windows PowerShell

```powershell
# 1. Move into the project directory
cd odd-even-hand-cricket

# 2. Create a virtual environment
py -m venv .venv

# 3. Activate it
.venv\Scripts\Activate.ps1

# 4. Install dependencies
python -m pip install -r requirements.txt

# 5. Start the server
python app.py
```

If PowerShell blocks activation, use Command Prompt:

```bat
.venv\Scripts\activate.bat
```

Open `http://127.0.0.1:5000` in two separate browser sessions. Create a room in one session and join it from the other. For local testing, a private/incognito window can represent the second player.

## 6. How the server and browser communicate

Main Socket.IO events:

| Event | Direction | Purpose |
|---|---|---|
| `create_room` | Browser → server | Create a room |
| `room_created` | Server → creator | Return room code |
| `join_room` | Browser → server | Join room |
| `joined_room` | Server → joining player | Confirm join |
| `state_update` | Server → both | Publish public match state |
| `select_number` | Browser → server | Update player's current selection |
| `your_selection` | Server → selecting player | Confirm own current selection |
| `round_reveal` | Server → both | Reveal the numbers after deadline |
| `choose_innings` | Toss winner → server | Choose batting or bowling |
| `match_over` | Server → both | Publish final result |

The server intentionally does not broadcast the current selected number to the other player. Only the reveal event contains both numbers.

## 7. Important current limitations

This starter is for learning and local testing. Before inviting people publicly, address these items:

1. **Reconnect support:** A room-scoped random player token is stored in sessionStorage and used to reattach after a page refresh in the same browser. Cross-device recovery and token rotation are future work.
2. **Timeout handling:** Current default ends the match if a player has not selected. Implement the agreed grace-period/forfeit policy.
3. **Match result correctness:** Add tests for both possible toss winners, both batting choices, wickets, target reached, ties and timeout scenarios.
4. **Second innings transitions:** Review and test all score/role transitions thoroughly before treating the game as complete.
5. **Room cleanup:** Remove abandoned rooms and expired games.
6. **Security:** Validate every event, bind players to their room identity, rate-limit events, use a strong secret key and disable debug mode in production.
7. **Deployment:** Use a host that supports WebSockets. Configure a production WSGI server and ensure Socket.IO is deployed with compatible settings.
8. **Multiple server instances:** In-memory rooms only work reliably with one server process. Use Redis or another shared state/message layer before scaling horizontally.
9. **HTTPS:** Use HTTPS/WSS for public deployment.
10. **External Socket.IO client:** The starter loads the Socket.IO browser client from a CDN. For production, pin and manage the client dependency deliberately.

## 8. Development roadmap

### Milestone 1 — Verify the rules engine
- [ ] Test odd/even toss calculation.
- [ ] Test that the latest selection replaces the earlier selection.
- [ ] Test that selections are captured only at the server deadline.
- [ ] Test matching numbers produce OUT.
- [ ] Test non-matching numbers add the batsman's number.
- [ ] Test target = first innings score + 1.
- [ ] Test all winner conditions.

### Milestone 2 — Complete multiplayer basics
- [ ] Robust room creation and joining.
- [ ] Player identity and reconnect tokens.
- [ ] Server-authoritative timer and round lifecycle.
- [ ] Prevent non-members from sending room actions.
- [ ] Grace period and timeout/forfeit handling.

### Milestone 3 — Improve the game interface
- [ ] Toss animation.
- [ ] Show batting and bowling roles.
- [ ] Improve scoreboard and target display.
- [ ] Ball-by-ball history.
- [ ] Responsive mobile layout.
- [ ] Sound effects and animations.

### Milestone 4 — Persistence and deployment
- [ ] SQLite match history.
- [ ] Player statistics and usernames.
- [ ] Shareable room links.
- [ ] Production hosting with WebSocket support.
- [ ] Monitoring, logging and error handling.

### Future ideas (optional)
- Spectator mode.
- Best-of-three matches.
- Custom themes.
- Player profile and avatar.
- Leaderboards and win/loss statistics.
- Private room password.
- Rematch button.
- Match commentary and sound effects.

## 9. Suggested Git workflow

```bash
git init
git add .
git commit -m "Initial hand cricket game scaffold"
```

Create a GitHub repository, then connect it:

```bash
git remote add origin YOUR_GITHUB_REPOSITORY_URL
git branch -M main
git push -u origin main
```

## 10. Project principle

Build the game in this order:

**Correct game logic → reliable two-player communication → complete match flow → polished UI → deployment.**

Do not spend the first week on animations or visual effects. A simple website that completes a correct match is the first real success.
