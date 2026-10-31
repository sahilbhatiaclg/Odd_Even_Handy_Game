import time

class HandCricketGame:
    """Server-authoritative rules engine for one two-player match."""

    def __init__(self, players):
        self.players = players
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
        self.out = {p["id"]: False for p in players}
        self.last_outcome = None

    def start_round(self, phase, seconds):
        self.phase = phase
        self.selections = {}
        self.deadline = time.time() + seconds
        self.round_token += 1
        self.message = f"{phase.replace('_', ' ').title()} selection is open."

    def set_selection(self, player_id, number):
        self.selections[player_id] = number

    def selection_status(self):
        return {"selected_count": len(self.selections), "player_count": len(self.players)}

    def scoreboard(self):
        labels = {p["id"]: f"Player {i + 1} - {p['name']}" for i, p in enumerate(self.players)}
        return {
            "scores": {labels[player_id]: score for player_id, score in self.scores.items()},
            "batting": labels.get(self.batting_id),
            "bowling": labels.get(self.bowling_id),
            "target": self.scores[self.first_innings_batting_id] + 1 if self.phase == "innings_2" and self.first_innings_batting_id else None
        }

    def resolve_round(self):
        self.deadline = None
        # A missing selection is treated as a timeout/forfeit, never as a valid cricket number.
        missing = [p["id"] for p in self.players if p["id"] not in self.selections]
        if missing:
            self.phase = "finished"
            winner = next((p["id"] for p in self.players if p["id"] not in missing), None)
            self.message = "A player did not select a number before time expired. Match ended by timeout."
            self.last_outcome = {"phase": "timeout", "missing": missing, "winner_id": winner}
            return self.last_outcome

        p1, p2 = self.players[0], self.players[1]
        n1, n2 = self.selections[p1["id"]], self.selections[p2["id"]]

        if self.phase == "toss":
            total = n1 + n2
            even_wins = total % 2 == 0
            winner = next(p for p in self.players if p["odd_even"] == ("even" if even_wins else "odd"))
            self.toss_winner = winner["id"]
            self.phase = "choose_innings"
            self.message = f"{winner['name']} won the toss and must choose batting or bowling."
            self.last_outcome = {
                "phase": "toss", "numbers": {p1["name"]: n1, p2["name"]: n2},
                "sum": total, "result": "even" if even_wins else "odd",
                "winner_name": winner["name"]
            }
            return self.last_outcome

        batsman = self.batting_id
        bowler = self.bowling_id
        bat_number = self.selections[batsman]
        bowl_number = self.selections[bowler]
        if bat_number == bowl_number:
            self.out[batsman] = True
            if self.phase == "innings_1":
                self.first_innings_batting_id = batsman
                self.phase = "innings_2"
                self.message = "First innings ended. Second innings begins."
            else:
                self.phase = "finished"
                self.message = "Second innings ended."
            outcome = {
                "phase": self.phase, "numbers": {
                    next(p["name"] for p in self.players if p["id"] == batsman): bat_number,
                    next(p["name"] for p in self.players if p["id"] == bowler): bowl_number
                },
                "runs": 0, "out": True, "score": self.scores[batsman],
                "message": self.message
            }
            self.last_outcome = outcome
            if self.phase == "innings_2":
                # roles switch after the first innings wicket
                self.batting_id, self.bowling_id = self.bowling_id, self.batting_id
                self.out = {p["id"]: False for p in self.players}
            return outcome

        self.scores[batsman] += bat_number
        target = self.scores[self.first_innings_batting_id] + 1 if self.phase == "innings_2" else None
        if self.phase == "innings_2" and self.scores[batsman] >= target:
            self.phase = "finished"
            self.message = "Target reached!"
        else:
            self.message = f"{bat_number} run(s) scored."
        self.last_outcome = {
            "phase": self.phase, "numbers": {
                next(p["name"] for p in self.players if p["id"] == batsman): bat_number,
                next(p["name"] for p in self.players if p["id"] == bowler): bowl_number
            },
            "runs": bat_number, "out": False, "score": self.scores[batsman],
            "target": target, "message": self.message
        }
        return self.last_outcome

    def choose_innings(self, player_id, choice):
        other_id = next(p["id"] for p in self.players if p["id"] != player_id)
        if choice == "bat":
            self.batting_id, self.bowling_id = player_id, other_id
        else:
            self.batting_id, self.bowling_id = other_id, player_id
        self.phase = "innings_1"
        self.message = "First innings started."

    def is_toss_winner(self, player_id):
        return player_id == self.toss_winner

    def match_result(self):
        p1, p2 = self.players
        s1, s2 = self.scores[p1["id"]], self.scores[p2["id"]]
        if s1 == s2:
            winner = None
            result = "Match tied."
        else:
            winner = p1 if s1 > s2 else p2
            result = f"{winner['name']} won the match."
        named_scores = {p["name"]: self.scores[p["id"]] for p in self.players}
        return {"scores": named_scores, "winner_name": winner["name"] if winner else None, "message": result}
