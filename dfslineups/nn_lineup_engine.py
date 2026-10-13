import numpy as np
from sklearn.neural_network import MLPClassifier

from dfslineups.models import Player, SerializedEntry


class NeuralLineupEngine:
    def __init__(self):
        # Binary classifier: WIN (1) vs LOSS (0)
        self.model = MLPClassifier(
            hidden_layer_sizes=(64, 32, 16),
            activation="relu",
            solver="adam",
            max_iter=500,
        )
        self.training_inputs = []
        self.training_outputs = []
        self.is_trained = False

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------
    def train(self):
        count = self._load_training_data()
        if count < 10:
            # Not enough data to train
            return False

        X = np.array(self.training_inputs)
        y = np.array(self.training_outputs)

        self.model.fit(X, y)
        self.is_trained = True
        return True

    def generate_lineups(self, salary_cap=50000, num_lineups=10, samples=300):
        """
        Generate candidate lineups from Player DB and score them
        using the trained neural network.
        """
        if not self.is_trained:
            # Try training on the fly
            if not self.train():
                return []

        qbs = list(Player.objects.filter(position="QB"))
        rbs = list(Player.objects.filter(position="RB"))
        wrs = list(Player.objects.filter(position="WR"))
        tes = list(Player.objects.filter(position="TE"))
        dsts = list(Player.objects.filter(position__in=["DST", "DEF"]))

        if not (qbs and rbs and wrs and tes and dsts):
            return []

        candidates = []

        for _ in range(samples):
            qb = np.random.choice(qbs)
            rb1 = np.random.choice(rbs)
            rb2 = np.random.choice(rbs)
            wr1 = np.random.choice(wrs)
            wr2 = np.random.choice(wrs)
            wr3 = np.random.choice(wrs)
            te = np.random.choice(tes)
            dst = np.random.choice(dsts)

            flex_pool = rbs + wrs + tes
            flex = np.random.choice(flex_pool)

            lineup_players = {
                "QB": qb,
                "RB1": rb1,
                "RB2": rb2,
                "WR1": wr1,
                "WR2": wr2,
                "WR3": wr3,
                "TE": te,
                "DST": dst,
                "FLEX": flex,
            }

            total_salary = sum(p.salary for p in lineup_players.values())
            if total_salary > salary_cap:
                continue

            features = self._extract_lineup_features(lineup_players)
            prob_win = self.model.predict_proba([features])[0][1]

            candidates.append({
                "score": float(prob_win),
                "total_salary": total_salary,
                "players": {
                    slot: {
                        "name": p.name,
                        "position": p.position,
                        "team": p.team,
                        "opponent": p.opponent,
                        "salary": p.salary,
                        "projection": p.projection,
                    }
                    for slot, p in lineup_players.items()
                }
            })

        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:num_lineups]

    # ------------------------------------------------------------
    # Training data loader
    # ------------------------------------------------------------
    def _load_training_data(self):
        self.training_inputs = []
        self.training_outputs = []

        entries = SerializedEntry.objects.all()

        for entry in entries:
            try:
                features = self._extract_features_from_entry(entry)
            except Exception:
                continue

            label = 1 if entry.entry_type == "WIN" else 0
            self.training_inputs.append(features)
            self.training_outputs.append(label)

        return len(self.training_inputs)

    # ------------------------------------------------------------
    # Feature extraction from SerializedEntry
    # ------------------------------------------------------------
    def _extract_features_from_entry(self, entry):
        """
        entry.data is your stored lineup JSON.
        We’ll treat it as a generic lineup and extract
        per-player features + aggregate features.
        """
        data = entry.data

        # Expect something like:
        # { "players": [ { "name": "...", "position": "...", "salary": ..., "projection": ..., "fpts": ... }, ... ],
        #   "total_salary": ...,
        #   "total_projection": ...,
        #   "total_points": ... }

        players = data.get("players") or data.get("lineup", {}).get("players") or []
        total_salary = data.get("total_salary", 0)
        total_projection = data.get("total_projection", 0)
        total_points = data.get("total_points", 0)

        feature_vector = []

        # Per-player features (limited to first 9 to match DK classic)
        for p in players[:9]:
            salary = float(p.get("salary", 0))
            proj = float(p.get("projection", p.get("fpts", 0)))
            pos = p.get("position", p.get("pos", "UNK"))
            team = p.get("team", "UNK")
            opp = p.get("opponent", "UNK")

            feature_vector.extend([
                salary,
                proj,
                self._encode_position(pos),
                self._encode_team(team),
                self._encode_team(opp),
            ])

        # Pad if fewer than 9 players
        while len(feature_vector) < 9 * 5:
            feature_vector.append(0.0)

        # Aggregate features
        feature_vector.extend([
            float(total_salary),
            float(total_projection),
            float(total_points),
        ])

        return np.array(feature_vector, dtype=float)

    # ------------------------------------------------------------
    # Feature extraction from Player lineup (for generation)
    # ------------------------------------------------------------
    def _extract_lineup_features(self, lineup_players):
        feature_vector = []

        order = ["QB", "RB1", "RB2", "WR1", "WR2", "WR3", "TE", "DST", "FLEX"]
        total_salary = 0.0
        total_projection = 0.0

        for slot in order:
            p = lineup_players[slot]
            salary = float(p.salary)
            proj = float(p.projection or 0.0)
            pos = p.position
            team = p.team
            opp = p.opponent

            total_salary += salary
            total_projection += proj

            feature_vector.extend([
                salary,
                proj,
                self._encode_position(pos),
                self._encode_team(team),
                self._encode_team(opp),
            ])

        # Aggregate features (no actual points yet, so 0)
        feature_vector.extend([
            total_salary,
            total_projection,
            0.0,  # total_points placeholder
        ])

        return np.array(feature_vector, dtype=float)

    # ------------------------------------------------------------
    # Encoders
    # ------------------------------------------------------------
    def _encode_position(self, pos):
        mapping = {
            "QB": 1,
            "RB": 2,
            "WR": 3,
            "TE": 4,
            "DST": 5,
            "DEF": 5,
            "FLEX": 6,
        }
        return float(mapping.get(pos, 0))

    def _encode_team(self, team):
        if not team:
            return 0.0
        return float(abs(hash(team)) % 1000)
