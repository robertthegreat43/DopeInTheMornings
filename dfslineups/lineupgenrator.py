import random


NFL_SLOTS = (
    ("QB", {"QB"}),
    ("RB", {"RB"}),
    ("RB", {"RB"}),
    ("WR", {"WR"}),
    ("WR", {"WR"}),
    ("WR", {"WR"}),
    ("TE", {"TE"}),
    ("FLEX", {"RB", "WR", "TE"}),
    ("DST", {"DST", "DEF"}),
)


def position_tokens(position):
    """Normalize common CSV position formats such as RB/WR or DEF."""
    aliases = {
        "DEFENSE": "DST",
        "DEFENCE": "DST",
        "D/ST": "DST",
        "POINTGUARD": "PG",
        "POINT GUARD": "PG",
        "SHOOTINGGUARD": "SG",
        "SHOOTING GUARD": "SG",
        "SMALLFORWARD": "SF",
        "SMALL FORWARD": "SF",
        "POWERFORWARD": "PF",
        "POWER FORWARD": "PF",
        "CENTER": "C",
    }
    tokens = (position or "").upper().replace(",", "/").split("/")
    normalized = set()
    for token in tokens:
        token = " ".join(token.strip().split())
        if token:
            normalized.add(aliases.get(token, token))
    return normalized


def load_players_from_db():
    """Load roster entries previously imported from the uploaded salary CSV."""
    from dfslineups.models import Player

    return list(Player.objects.all().values(
        "name", "position", "team", "salary", "projection"
    ))


def nfl_position_issues(players):
    """Return missing/insufficient NFL roster positions for a DraftKings lineup."""
    counts = {"QB": 0, "RB": 0, "WR": 0, "TE": 0, "DST": 0}
    for player in players:
        positions = position_tokens(player.get("position"))
        for position in counts:
            if position in positions or (position == "DST" and "DEF" in positions):
                counts[position] += 1

    needs = {"QB": 1, "RB": 2, "WR": 3, "TE": 1, "DST": 1}
    return [f"{position} (need {needed}, found {counts[position]})"
            for position, needed in needs.items() if counts[position] < needed]


def generate_dk_valid_lineup(players, salary_cap=50000, max_nodes=100000):
    """Find a unique-player NFL DraftKings lineup satisfying roster and salary rules."""
    if nfl_position_issues(players):
        return None

    slots = list(NFL_SLOTS)
    best_lineup = None
    best_projection = float("-inf")
    nodes = 0

    def search(remaining, chosen, used, salary, projection):
        nonlocal best_lineup, best_projection, nodes
        if nodes >= max_nodes:
            return
        if not remaining:
            if projection > best_projection:
                best_projection = projection
                best_lineup = [chosen[slot] for slot, _ in slots]
            return

        # Pick the most constrained remaining slot first. This still returns the
        # lineup in the original QB/RB/WR/TE/FLEX/DST order above.
        options = []
        for slot_index, (slot, eligible_positions) in enumerate(remaining):
            candidates = [
                player for player in players
                if id(player) not in used
                and position_tokens(player.get("position")) & eligible_positions
                and salary + int(player.get("salary") or 0) <= salary_cap
            ]
            options.append((len(candidates), slot_index, slot, candidates))
        _, slot_index, slot, candidates = min(options, key=lambda item: item[0])
        if not candidates:
            return

        candidates.sort(key=lambda player: float(player.get("projection") or 0), reverse=True)
        next_remaining = remaining[:slot_index] + remaining[slot_index + 1:]
        for player in candidates:
            nodes += 1
            player_salary = int(player.get("salary") or 0)
            player_projection = float(player.get("projection") or 0)
            chosen[slot] = player
            used.add(id(player))
            search(next_remaining, chosen, used,
                   salary + player_salary, projection + player_projection)
            used.remove(id(player))
            del chosen[slot]
            if nodes >= max_nodes:
                break

    search(slots, {}, set(), 0, 0.0)
    return best_lineup


def print_lineup(lineup, number):
    print(f"\n================ DK LINEUP {number} ================")
    total_salary = sum(int(player.get("salary") or 0) for player in lineup)
    total_projection = sum(float(player.get("projection") or 0) for player in lineup)
    for player in lineup:
        print(
            f"{player['position']:8}  {player['name']:25}  "
            f"${int(player.get('salary') or 0):5}  "
            f"proj={float(player.get('projection') or 0)}"
        )
    print("-----------------------------------------------")
    print("Total Salary:", total_salary)
    print("Total Projection:", total_projection)
    print("===============================================\n")


if __name__ == "__main__":
    import os
    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Podcastdope.dev")
    django.setup()
    players = load_players_from_db()
    print("Loaded", len(players), "players from database.")
    lineup = generate_dk_valid_lineup(players)
    if lineup:
        print_lineup(lineup, 1)
    else:
        print("Could not generate an NFL lineup: check DraftKings position and salary rules.")
