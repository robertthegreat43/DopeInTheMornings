from __future__ import annotations

import random


SALARY_CAP = 50_000
SEARCH_NODE_LIMIT = 100_000
UNAVAILABLE_STATUSES = {"OUT", "O", "IR", "INACTIVE", "SUSPENDED"}
MLB_SLOTS = ("P", "P", "C", "1B", "2B", "3B", "SS", "OF", "OF", "OF")
TENNIS_SLOTS = ("TENNIS",) * 6


def _position_tokens(value):
    return {
        token.strip().upper()
        for token in (value or "").replace(",", "/").split("/")
        if token.strip()
    }


def _available(player):
    return (player.get("status") or "").strip().upper() not in UNAVAILABLE_STATUSES


def _salary(player):
    return int(player.get("salary") or 0)


def _projection(player):
    return float(player.get("projection") or 0)


def _optimize(slots, eligible, *, team_limit=None, match_limit=None):
    """Bounded DFS; enforces salary, unique players, and optional sport limits."""
    search_slots = sorted(slots, key=lambda slot: len(eligible[slot]))
    if any(not eligible[slot] for slot in search_slots):
        return None

    max_projection = {
        slot: max(_projection(player) for player in eligible[slot])
        for slot in search_slots
    }
    best_lineup = None
    best_projection = float("-inf")
    visited = 0
    chosen = {}
    team_counts = {}
    match_counts = {}

    def search(index, used_ids, salary, projection):
        nonlocal visited, best_lineup, best_projection
        if visited >= SEARCH_NODE_LIMIT:
            return
        visited += 1

        if index == len(search_slots):
            if projection > best_projection:
                best_projection = projection
                best_lineup = dict(chosen)
            return

        if projection + sum(max_projection[slot] for slot in search_slots[index:]) <= best_projection:
            return

        slot = search_slots[index]
        candidates = [p for p in eligible[slot] if p["id"] not in used_ids]
        random.shuffle(candidates)
        candidates.sort(key=_projection, reverse=True)

        for player in candidates:
            player_salary = _salary(player)
            if player_salary < 0 or salary + player_salary > SALARY_CAP:
                continue

            team = (player.get("team") or "").strip().upper()
            if team_limit is not None and team and team_counts.get(team, 0) >= team_limit:
                continue

            match = (player.get("match_id") or "").strip()
            if match_limit is not None and match and match_counts.get(match, 0) >= match_limit:
                continue

            chosen[slot] = player
            used_ids.add(player["id"])
            if team:
                team_counts[team] = team_counts.get(team, 0) + 1
            if match:
                match_counts[match] = match_counts.get(match, 0) + 1

            search(index + 1, used_ids, salary + player_salary, projection + _projection(player))

            if team:
                team_counts[team] -= 1
            if match:
                match_counts[match] -= 1
            used_ids.remove(player["id"])
            del chosen[slot]
            if visited >= SEARCH_NODE_LIMIT:
                break

    search(0, set(), 0, 0.0)
    if best_lineup is None:
        return None
    return [best_lineup[slot] for slot in slots]


def generate_mlb_lineup(players):
    available = [player for player in players if _available(player)]
    pools = {
        pos: [player for player in available if pos in _position_tokens(player.get("position"))]
        for pos in ("P", "C", "1B", "2B", "3B", "SS", "OF")
    }
    counts = {pos: len(pool) for pos, pool in pools.items()}
    if counts["P"] < 2 or any(counts[pos] < 1 for pos in ("C", "1B", "2B", "3B", "SS")) or counts["OF"] < 3:
        return None, counts

    eligible = {"P": pools["P"], "C": pools["C"], "1B": pools["1B"],
                "2B": pools["2B"], "3B": pools["3B"], "SS": pools["SS"], "OF": pools["OF"]}
    lineup = _optimize(MLB_SLOTS, eligible, team_limit=5)
    return lineup, counts


def generate_tennis_lineup(players):
    available = [player for player in players if _available(player)]
    eligible = {"TENNIS": available}
    lineup = _optimize(TENNIS_SLOTS, eligible, match_limit=4)
    return lineup, {"players": len(available)}


def serialize_lineup(slots, lineup):
    result = []
    for slot, player in zip(slots, lineup):
        result.append({
            "slot": slot,
            "name": player.get("name", ""),
            "position": player.get("position", ""),
            "team": player.get("team", ""),
            "salary": _salary(player),
            "projection": _projection(player),
        })
    return {
        "players": result,
        "total_salary": sum(player["salary"] for player in result),
        "total_projection": round(sum(player["projection"] for player in result), 2),
    }
