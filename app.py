import os
import re
import threading
from flask import Flask, redirect, render_template, request
from flask_socketio import SocketIO, emit, join_room
from game.engine import HandCricketGame
from rooms.room_manager import RoomManager

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-development-secret")
# cors "*" is fine for local play; restrict it before a public deployment.
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

MIN_TIMER, MAX_TIMER = 5, 60
REVEAL_PAUSE_SECONDS = 3  # time to read the result before the next round starts
ROOM_ID_RE = re.compile(r"^[A-Z0-9]{6}$")

rooms = RoomManager()
games = {}
lock = threading.RLock()  # socket handlers and round timers run in different threads


# ---------------------------------------------------------------- pages
@app.get("/")
def index():
    return render_template("index.html")


@app.get("/game/<room_id>")
def game_page(room_id):
    room_id = room_id.upper()
    if not ROOM_ID_RE.match(room_id):
        return redirect("/")
    return render_template("game.html", room_id=room_id)


# -------------------------------------------------------------- helpers
def as_dict(data):
    return data if isinstance(data, dict) else {}


def clean_name(value, fallback):
    return str(value or "").strip()[:24] or fallback


def clean_room_id(value):
    return str(value or "").strip().upper()


def public_state(room_id):
    """What both players are allowed to see. Never includes anyone's current pick."""
    room = rooms.get(room_id)
    if not room:
        return None
    game = games.get(room_id)
    players = [
        {"name": p["name"], "odd_even": p["odd_even"], "connected": p["connected"]}
        for p in room["players"]
    ]
    if game:
        message = game.message
        phase = game.phase
    elif len(room["players"]) < 2:
        message, phase = "Waiting for a friend to join. Share the room code!", "waiting"
    else:
        message, phase = "Waiting for both players to connect.", "waiting"
    if game and phase == "waiting":
        message = "Waiting for both players to connect."
    away = [p["name"] for p in room["players"] if not p["connected"]]
    return {
        "room_id": room["room_id"],
        "players": players,
        "phase": phase,
        "timer_seconds": room["timer_seconds"],
        "seconds_left": game.seconds_left() if game else None,  # server-computed, avoids clock skew
        "round_no": game.round_token if game else 0,
        "toss_winner": game.index_of(game.toss_winner) if game and game.toss_winner else None,
        "score": game.scoreboard() if game else None,
        "message": message,
        "notice": f"{', '.join(away)} disconnected. Waiting for them to come back." if away and phase not in ("waiting", "finished") else "",
    }


def broadcast_state(room_id):
    state = public_state(room_id)
    if state:
        socketio.emit("state_update", state, to=room_id)


def error(message, code=None):
    emit("error_message", {"message": message, "code": code})


def start_round(room_id, phase):
    """Must be called with `lock` held."""
    game, room = games.get(room_id), rooms.get(room_id)
    if not game or not room:
        return
    game.start_round(phase, room["timer_seconds"])
    broadcast_state(room_id)
    socketio.start_background_task(finish_round_after_delay, room_id, game.round_token, game.seconds_left())


def maybe_start_game(room_id):
    """Start the toss once both players are on the game page. Must hold `lock`."""
    game = games.get(room_id)
    if game and game.phase == "waiting" and rooms.both_connected(room_id):
        start_round(room_id, "toss")


def finish_round_after_delay(room_id, token, delay):
    socketio.sleep(delay)
    with lock:
        game = games.get(room_id)
        # Ignore stale timers (a newer round started) and rounds already resolved.
        if not game or game.round_token != token or game.deadline is None:
            return
        outcome = game.resolve_round()
        socketio.emit("round_reveal", outcome, to=room_id)
        broadcast_state(room_id)
        phase = game.phase
        if phase == "finished":
            socketio.emit("match_over", game.match_result(), to=room_id)
            return
        if phase == "choose_innings":
            return  # wait for the toss winner's decision
    # Another ball (or the second innings) follows: let players read the result first.
    socketio.sleep(REVEAL_PAUSE_SECONDS)
    with lock:
        game = games.get(room_id)
        if game and game.round_token == token and game.phase == phase and game.deadline is None:
            start_round(room_id, phase)


# --------------------------------------------------------- socket events
@socketio.on("create_room")
def create_room(data):
    data = as_dict(data)
    name = clean_name(data.get("name"), "Player 1")
    try:
        timer = int(data.get("timer_seconds", 10))
    except (TypeError, ValueError):
        timer = 10
    timer = max(MIN_TIMER, min(MAX_TIMER, timer))
    odd_even = data.get("odd_even") if data.get("odd_even") in ("odd", "even") else "odd"
    with lock:
        room, token = rooms.create(request.sid, name, timer, odd_even)
        join_room(room["room_id"])
    emit("room_created", {"room_id": room["room_id"], "player_token": token, "you": 0})
    broadcast_state(room["room_id"])


@socketio.on("join_room")
def join_existing_room(data):
    data = as_dict(data)
    room_id = clean_room_id(data.get("room_id"))
    name = clean_name(data.get("name"), "Player 2")
    with lock:
        room, token, err = rooms.join(room_id, request.sid, name)
        if err:
            error(err)
            return
        join_room(room_id)
        games[room_id] = HandCricketGame(room["players"])
    emit("joined_room", {"room_id": room_id, "player_token": token, "you": 1})
    broadcast_state(room_id)
    # The toss starts after both players have loaded the game page (see reconnect_player).


@socketio.on("reconnect_player")
def reconnect_player(data):
    data = as_dict(data)
    room_id = clean_room_id(data.get("room_id"))
    token = str(data.get("player_token") or "")
    with lock:
        player, err = rooms.reconnect(room_id, request.sid, token)
        if err:
            error(err, code="session_invalid")
            return
        join_room(room_id)
        emit("reconnected", {"room_id": room_id, "you": rooms.player_index(room_id, token)})
        game = games.get(room_id)
        if game and game.selection_for(player["id"]) is not None:
            emit("your_selection", {"number": game.selection_for(player["id"])})
        broadcast_state(room_id)
        maybe_start_game(room_id)


@socketio.on("select_number")
def select_number(data):
    data = as_dict(data)
    room_id = clean_room_id(data.get("room_id"))
    number = data.get("number")
    if isinstance(number, bool) or not isinstance(number, int) or not 1 <= number <= 6:
        error("Choose a number from 1 to 6.")
        return
    with lock:
        game = games.get(room_id)
        if not game:
            error("Room or game not found.")
            return
        player_id = game.player_id_for_sid(request.sid)
        if player_id is None:
            error("You are not a player in this room.")
            return
        if not game.set_selection(player_id, number):
            error("Number selection is not open right now.")
            return
    # Only the player who clicked gets this back. The opponent is never told.
    emit("your_selection", {"number": number})


@socketio.on("choose_innings")
def choose_innings(data):
    data = as_dict(data)
    room_id = clean_room_id(data.get("room_id"))
    with lock:
        game = games.get(room_id)
        if not game:
            error("Room or game not found.")
            return
        player_id = game.player_id_for_sid(request.sid)
        if player_id is None or not game.choose_innings(player_id, data.get("choice")):
            error("Only the toss winner can choose, and only after the toss.")
            return
        start_round(room_id, game.phase)


@socketio.on("disconnect")
def disconnect():
    with lock:
        room_id = rooms.room_for_player(request.sid)
        if room_id:
            rooms.mark_disconnected(room_id, request.sid)
            broadcast_state(room_id)


if __name__ == "__main__":
    # Safe defaults: local only, debug off. For friends on your Wi-Fi: set HOST=0.0.0.0
    # For auto-reload while editing: set FLASK_DEBUG=1 (note: a reload wipes all rooms).
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)