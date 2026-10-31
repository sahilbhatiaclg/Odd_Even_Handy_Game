import time

ROUND_PHASES = ("toss", "innings_1", "innings_2")


class HandCricketGame:
    """Server-authoritative rules engine for one two-player match.

    Everything is keyed by the player's private id (their token), never by the
    socket id, because a socket id changes whenever the browser reconnects.
    """

    def __init__(self, players):
        self.players = players  # same list object the room uses
        self.phase = "waiting"
        self.deadline = None
        self.round_token = 0
        self.selections = {}
        self.message = "Waiting for toss."
        self.toss_winner = None
        self.batting_id = None
        self.bowling_id = None
        self.first_innings_batting_id = None
        self.scores = {p["id"]: 0 for p in players}
        self.ended_by_timeout = False
        self.timeout_winner_id = None

    # ---- lookups -------------------------------------------------------
    def player_id_for_sid(self, sid):
        return next((p["id"] for p in self.players if p.get("sid") == sid), None)

    def name_of(self, player_id):
        return next((p["name"] for p in self.players if p["id"] == player_id), "?")

    def index_of(self, player_id):
        return next((i for i, p in enumerate(self.players) if p["id"] == player_id), None)

    # ---- rounds --------------------------------------------------------
    def start_round(self, phase, seconds):
        self.phase = phase
        self.selections = {}
        self.deadline = time.time() + seconds
        self.round_token += 1
        if phase == "toss":
            self.message = "Toss: pick a number from 1 to 6."
        else:
            self.message = f"{self.name_of(self.batting_id)} is batting, {self.name_of(self.bowling_id)} is bowling."

    def seconds_left(self):
        if self.deadline is None:
            return None
        return max(0.0, self.deadline - time.time())

    def selection_open(self):
        return self.phase in ROUND_PHASES and self.deadline is not None and time.time() < self.deadline

    def set_selection(self, player_id, number):
        if not self.selection_open():
            return False
        self.selections[player_id] = number  # latest click wins
        return True

    def selection_for(self, player_id):
        return self.selections.get(player_id)

    def scoreboard(self):
        show_roles = self.phase in ("innings_1", "innings_2")
        players = []
        for p in self.players:
            role = None
            if show_roles:
                role = "bat" if p["id"] == self.batting_id else "bowl"
            players.append({"name": p["name"], "score": self.scores[p["id"]], "role": role})
        return {"players": players, "target": self.target()}

    def target(self):
        if self.phase == "innings_2" and self.first_innings_batting_id:
            return self.scores[self.first_innings_batting_id] + 1
        return None

    # ---- resolving a round --------------------------------------------
    def resolve_round(self):
        """Called by the server when the deadline passes. Uses each player's latest pick."""
        self.deadline = None
        missing = [p for p in self.players if p["id"] not in self.selections]
        if missing:
            # Timeout policy (still to be finalised): a player who never picked forfeits.
            self.ended_by_timeout = True
            self.phase = "finished"
            present = [p for p in self.players if p not in missing]
            self.timeout_winner_id = present[0]["id"] if len(present) == 1 else None
            names = " and ".join(p["name"] for p in missing)
            self.message = f"{names} did not pick a number in time."
            return {"kind": "timeout", "missing_names": [p["name"] for p in missing], "message": self.message}

        if self.phase == "toss":
            return self._resolve_toss()
        return self._resolve_ball()

    def _resolve_toss(self):
        p1, p2 = self.players
        n1, n2 = self.selections[p1["id"]], self.selections[p2["id"]]
        total = n1 + n2
        result = "even" if total % 2 == 0 else "odd"
        winner = next(p for p in self.players if p["odd_even"] == result)
        self.toss_winner = winner["id"]
        self.phase = "choose_innings"
        self.message = f"{winner['name']} won the toss and chooses bat or bowl."
        return {
            "kind": "toss",
            "numbers": [{"name": p1["name"], "number": n1}, {"name": p2["name"], "number": n2}],
            "sum": total, "result": result, "winner_name": winner["name"],
            "message": f"{n1} + {n2} = {total} ({result.upper()}). {winner['name']} wins the toss.",
        }

    def _resolve_ball(self):
        innings = 1 if self.phase == "innings_1" else 2
        bat_id, bowl_id = self.batting_id, self.bowling_id
        bat_n, bowl_n = self.selections[bat_id], self.selections[bowl_id]
        bat_name = self.name_of(bat_id)
        outcome = {
            "kind": "ball", "innings": innings,
            "batsman": {"name": bat_name, "number": bat_n},
            "bowler": {"name": self.name_of(bowl_id), "number": bowl_n},
        }

        if bat_n == bowl_n:  # OUT
            score = self.scores[bat_id]
            outcome.update(out=True, runs=0, score=score)
            if innings == 1:
                self.first_innings_batting_id = bat_id
                self.batting_id, self.bowling_id = bowl_id, bat_id  # roles swap
                self.phase = "innings_2"
                self.message = f"{bat_name} is OUT for {score}. Target is {score + 1}."
            else:
                self.phase = "finished"
                self.message = f"{bat_name} is OUT for {score}."
        else:
            self.scores[bat_id] += bat_n
            score = self.scores[bat_id]
            outcome.update(out=False, runs=bat_n, score=score)
            if innings == 2 and score >= self.scores[self.first_innings_batting_id] + 1:
                self.phase = "finished"
                self.message = f"{bat_name} reached the target!"
            else:
                self.message = f"{bat_n} run(s). {bat_name} has {score}."
        outcome["target"] = self.scores[self.first_innings_batting_id] + 1 if innings == 2 else None
        outcome["message"] = self.message
        return outcome

    # ---- toss decision -------------------------------------------------
    def choose_innings(self, player_id, choice):
        """Returns True if accepted. Only the toss winner may choose, and only once."""
        if self.phase != "choose_innings" or player_id != self.toss_winner or choice not in ("bat", "bowl"):
            return False
        other_id = next(p["id"] for p in self.players if p["id"] != player_id)
        if choice == "bat":
            self.batting_id, self.bowling_id = player_id, other_id
        else:
            self.batting_id, self.bowling_id = other_id, player_id
        self.phase = "innings_1"  # app.py starts the round right after this
        return True

    # ---- final result --------------------------------------------------
    def match_result(self):
        scores = [{"name": p["name"], "score": self.scores[p["id"]]} for p in self.players]
        if self.ended_by_timeout:
            if self.timeout_winner_id:
                winner = self.name_of(self.timeout_winner_id)
                return {"scores": scores, "winner_name": winner, "message": f"{winner} wins. The other player ran out of time."}
            return {"scores": scores, "winner_name": None, "message": "Neither player picked in time. No result."}
        s1, s2 = (self.scores[p["id"]] for p in self.players)
        if s1 == s2:
            return {"scores": scores, "winner_name": None, "message": f"Match tied at {s1}."}
        winner = self.players[0] if s1 > s2 else self.players[1]
        return {"scores": scores, "winner_name": winner["name"], "message": f"{winner['name']} wins the match!"}