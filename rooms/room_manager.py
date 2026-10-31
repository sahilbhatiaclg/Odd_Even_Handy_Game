import secrets

# No 0/O or 1/I so room codes are easy to read out loud.
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


class RoomManager:
    def __init__(self):
        self.rooms = {}

    def _new_code(self):
        while True:
            code = "".join(secrets.choice(ALPHABET) for _ in range(6))
            if code not in self.rooms:
                return code

    def create(self, sid, name, timer_seconds, creator_odd_even):
        code = self._new_code()
        token = secrets.token_urlsafe(24)
        room = {
            "room_id": code,
            "timer_seconds": timer_seconds,
            "players": [{
                "id": token, "sid": sid, "name": name,
                "odd_even": creator_odd_even, "connected": False,  # becomes True when the game page connects
            }],
        }
        self.rooms[code] = room
        return room, token

    def join(self, room_id, sid, name):
        room = self.rooms.get(room_id)
        if not room:
            return None, None, "Room not found. Check the code and try again."
        if len(room["players"]) >= 2:
            return None, None, "This room already has two players."
        first = room["players"][0]
        if name.strip().lower() == first["name"].strip().lower():
            name = f"{name[:20]} (2)"  # keep the two names distinguishable
        opposite = "even" if first["odd_even"] == "odd" else "odd"
        token = secrets.token_urlsafe(24)
        room["players"].append({
            "id": token, "sid": sid, "name": name,
            "odd_even": opposite, "connected": False,  # becomes True when the game page connects
        })
        return room, token, None

    def reconnect(self, room_id, sid, token):
        room = self.get(room_id)
        if not room:
            return None, "Room not found. It may have been closed when the server restarted."
        player = next((p for p in room["players"] if p["id"] == token), None)
        if not player:
            return None, "Player session not recognized."
        player["sid"] = sid
        player["connected"] = True
        return player, None

    def get(self, room_id):
        return self.rooms.get(room_id)

    def player_index(self, room_id, token):
        room = self.get(room_id)
        if not room:
            return None
        return next((i for i, p in enumerate(room["players"]) if p["id"] == token), None)

    def room_for_player(self, sid):
        for code, room in self.rooms.items():
            if any(p.get("sid") == sid for p in room["players"]):
                return code
        return None

    def mark_disconnected(self, room_id, sid):
        room = self.get(room_id)
        if room:
            for player in room["players"]:
                if player.get("sid") == sid:
                    player["connected"] = False

    def both_connected(self, room_id):
        room = self.get(room_id)
        return bool(room and len(room["players"]) == 2 and all(p["connected"] for p in room["players"]))