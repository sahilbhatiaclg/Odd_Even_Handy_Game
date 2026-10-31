import secrets
import string

class RoomManager:
    def __init__(self):
        self.rooms = {}

    def _new_code(self):
        alphabet = string.ascii_uppercase + string.digits
        while True:
            code = "".join(secrets.choice(alphabet) for _ in range(6))
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
                "odd_even": creator_odd_even, "connected": True
            }]
        }
        self.rooms[code] = room
        return room, token

    def join(self, room_id, sid, name):
        room = self.rooms.get(room_id)
        if not room:
            return None, None, "Room not found."
        if len(room["players"]) >= 2:
            return None, None, "This room already has two players."
        opposite = "even" if room["players"][0]["odd_even"] == "odd" else "odd"
        token = secrets.token_urlsafe(24)
        room["players"].append({
            "id": token, "sid": sid, "name": name,
            "odd_even": opposite, "connected": True
        })
        return room, token, None

    def reconnect(self, room_id, sid, token):
        room = self.get(room_id)
        if not room:
            return None, "Room not found."
        player = next((p for p in room["players"] if p["id"] == token), None)
        if not player:
            return None, "Player session not recognized."
        player["sid"] = sid
        player["connected"] = True
        return player, None

    def get(self, room_id):
        return self.rooms.get(room_id)

    def is_player(self, room_id, sid):
        room = self.get(room_id)
        return bool(room and any(p.get("sid") == sid for p in room["players"]))

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
