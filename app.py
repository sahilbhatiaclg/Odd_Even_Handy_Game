import os
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from game.engine import HandCricketGame
from rooms.room_manager import RoomManager

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-development-secret")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

rooms = RoomManager()
games = {}

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/game/<room_id>")
def game_page(room_id):
    return render_template("game.html", room_id=room_id.upper())

def public_state(room_id):
    room = rooms.get(room_id)
    if not room:
        return None
    game = games.get(room_id)
    result = {
        "room_id": room["room_id"],
        "players": [
            {"name": p["name"], "odd_even": p["odd_even"]}
            for p in room["players"]
        ],
        "phase": game.phase if game else "waiting",
        "timer_seconds": room["timer_seconds"],
        "deadline": game.deadline if game else None,
        "selection": game.selection_status() if game else {},
        "score": game.scoreboard() if game else None,
        "message": game.message if game else "Waiting for the second player."
    }
    return result

def broadcast_state(room_id):
    state = public_state(room_id)
    if state:
        socketio.emit("state_update", state, to=room_id)

def start_round(room_id, phase):
    game = games.get(room_id)
    if not game:
        return
    game.start_round(phase, rooms.get(room_id)["timer_seconds"])
    broadcast_state(room_id)
    delay = max(0, game.deadline - __import__("time").time())
    socketio.start_background_task(finish_round_after_delay, room_id, game.round_token, delay)

def finish_round_after_delay(room_id, token, delay):
    socketio.sleep(delay)
    game = games.get(room_id)
    if not game or game.round_token != token or game.phase in ("waiting", "finished", "choose_innings"):
        return
    outcome = game.resolve_round()
    socketio.emit("round_reveal", outcome, to=room_id)
    broadcast_state(room_id)

    if game.phase == "finished":
        socketio.emit("match_over", game.match_result(), to=room_id)
        broadcast_state(room_id)
    elif game.phase == "choose_innings":
        broadcast_state(room_id)
    elif game.phase in ("innings_1", "innings_2"):
        start_round(room_id, game.phase)

@socketio.on("create_room")
def create_room(data):
    name = (data.get("name") or "Player 1").strip()[:24]
    timer = max(5, min(60, int(data.get("timer_seconds", 10))))
    odd_even = data.get("odd_even", "odd")
    room, token = rooms.create(request.sid, name, timer, odd_even)
    join_room(room["room_id"])
    emit("room_created", {"room_id": room["room_id"], "player_token": token})
    broadcast_state(room["room_id"])

@socketio.on("join_room")
def join_existing_room(data):
    room_id = (data.get("room_id") or "").strip().upper()
    name = (data.get("name") or "Player 2").strip()[:24]
    room, token, error = rooms.join(room_id, request.sid, name)
    if error:
        emit("error_message", {"message": error})
        return
    join_room(room_id)
    games[room_id] = HandCricketGame(room["players"])
    emit("joined_room", {"room_id": room_id, "player_token": token})
    broadcast_state(room_id)
    socketio.emit("game_message", {"message": "Both players joined. Toss begins!"}, to=room_id)
    start_round(room_id, "toss")

@socketio.on("reconnect_player")
def reconnect_player(data):
    room_id = (data.get("room_id") or "").upper()
    token = data.get("player_token") or ""
    player, error = rooms.reconnect(room_id, request.sid, token)
    if error:
        emit("error_message", {"message": error})
        return
    join_room(room_id)
    emit("reconnected", {"room_id": room_id})
    broadcast_state(room_id)

@socketio.on("select_number")
def select_number(data):
    room_id = (data.get("room_id") or "").upper()
    number = data.get("number")
    game = games.get(room_id)
    room = rooms.get(room_id)
    if not game or not room:
        emit("error_message", {"message": "Room or game not found."})
        return
    if not isinstance(number, int) or number not in range(1, 7):
        emit("error_message", {"message": "Choose a number from 1 to 6."})
        return
    if game.phase not in ("toss", "innings_1", "innings_2") or game.deadline is None:
        emit("error_message", {"message": "Number selection is not open right now."})
        return
    import time
    if time.time() >= game.deadline:
        emit("error_message", {"message": "The selection deadline has passed."})
        return
    if not rooms.is_player(room_id, request.sid):
        emit("error_message", {"message": "You are not a player in this room."})
        return
    game.set_selection(request.sid, number)
    # Send the current selection only to the player who made it.
    emit("your_selection", {"number": number})

@socketio.on("choose_innings")
def choose_innings(data):
    room_id = (data.get("room_id") or "").upper()
    choice = data.get("choice")
    game = games.get(room_id)
    if not game or game.phase != "choose_innings":
        emit("error_message", {"message": "The toss decision is not available."})
        return
    if choice not in ("bat", "bowl"):
        emit("error_message", {"message": "Choose batting or bowling."})
        return
    if not game.is_toss_winner(request.sid):
        emit("error_message", {"message": "Only the toss winner can make this choice."})
        return
    game.choose_innings(request.sid, choice)
    broadcast_state(room_id)
    start_round(room_id, game.phase)

@socketio.on("disconnect")
def disconnect():
    room_id = rooms.room_for_player(request.sid)
    if room_id:
        rooms.mark_disconnected(room_id, request.sid)
        socketio.emit("game_message", {"message": "A player disconnected. They may reconnect by rejoining the room."}, to=room_id)
        broadcast_state(room_id)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True, allow_unsafe_werkzeug=True)
