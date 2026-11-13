import random

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from .models import Player


# DraftKings NBA roster slots. The Position column contains every eligible
# position for a player (for example, PG/SG or PF/C); a player may fill any one
# matching slot, but may only appear once in the lineup.
NBA_SLOTS = (
    ("PG", {"PG"}),
    ("SG", {"SG"}),
    ("SF", {"SF"}),
    ("PF", {"PF"}),
    ("C", {"C", "CENTER"}),
    ("G", {"PG", "SG"}),
    ("F", {"SF", "PF", "F", "FORWARD"}),
    ("UTIL", {"PG", "SG", "SF", "PF", "F", "FORWARD", "C", "CENTER"}),
)
PLAYER_FIELDS = ("id", "name", "position", "team", "salary", "projection", "status")
NBA_NODE_LIMIT = 30000
NFL_ATTEMPTS = 1000


def _position_tokens(position):
    """Normalize single- or multi-position CSV values such as 'PG/SG' and 'PF,C'."""
    return {token.strip().upper() for token in (position or "").replace(",", "/").split("/") if token.strip()}


def _is_unavailable(player):
    status = (player.get("status") or "").strip().upper()
    return status in {"OUT", "O", "IR", "INACTIVE", "SUSPENDED"}


def _serialize_lineup(slots, lineup):
    players = []
    for slot, player in zip(slots, lineup):
        players.append({
            "slot": slot,
            "position": player["position"],
            "name": player["name"],
            "team": player["team"],
            "salary": int(player["salary"] or 0),
            "projection": float(player["projection"] or 0),
        })
    return {
        "players": players,
        "total_salary": sum(player["salary"] for player in players),
        "total_projection": round(sum(player["projection"] for player in players), 2),
    }


def _find_best_lineup(slots, eligible, salary_cap=50000, node_limit=NBA_NODE_LIMIT):
    """Bounded DFS that assigns multi-position players once and respects the cap."""
    # Fill the most restrictive slots first. Keep original slot order for output.
    search_slots = sorted(slots, key=lambda slot: len(eligible[slot]))
    max_projection = {
        slot: max((float(p["projection"] or 0) for p in eligible[slot]), default=0)
        for slot in search_slots
    }
    best_lineup = None
    best_projection = float("-inf")
    visited = 0
    chosen = {}

    def search(index, used_ids, salary, projection):
        nonlocal visited, best_lineup, best_projection
        if visited >= node_limit:
            return
        visited += 1

        if index == len(search_slots):
            if projection > best_projection:
                best_projection = projection
                best_lineup = dict(chosen)
            return

        # Optimistic bound: even the best projection at every remaining slot
        # cannot improve the current solution, so this branch is unnecessary.
        upper_bound = projection + sum(max_projection[s] for s in search_slots[index:])
        if upper_bound <= best_projection:
            return

        slot = search_slots[index]
        candidates = [p for p in eligible[slot] if p["id"] not in used_ids]
        # Randomize ties so repeated requests can produce different lineups.
        random.shuffle(candidates)
        candidates.sort(key=lambda p: float(p["projection"] or 0), reverse=True)

        for player in candidates:
            player_salary = int(player["salary"] or 0)
            if salary + player_salary > salary_cap:
                continue
            chosen[slot] = player
            used_ids.add(player["id"])
            search(
                index + 1,
                used_ids,
                salary + player_salary,
                projection + float(player["projection"] or 0),
            )
            used_ids.remove(player["id"])
            del chosen[slot]
            if visited >= node_limit:
                break

    search(0, set(), 0, 0.0)
    if best_lineup is None:
        return None, visited
    return [best_lineup[slot] for slot in slots], visited


@require_GET
def generate_nfl_lines(request):
    """Generate a DraftKings NFL lineup without slow Django model comparisons."""
    players = list(Player.objects.values(*PLAYER_FIELDS))
    positions = {
        "QB": {"QB"},
        "RB": {"RB"},
        "WR": {"WR"},
        "TE": {"TE"},
        "DST": {"DST", "DEF"},
    }
    pools = {
        position: [p for p in players if not _is_unavailable(p) and _position_tokens(p["position"]) & tokens]
        for position, tokens in positions.items()
    }
    counts = {position: len(pool) for position, pool in pools.items()}
    if counts["QB"] < 1 or counts["RB"] < 2 or counts["WR"] < 3 or counts["TE"] < 1 or counts["DST"] < 1:
        return JsonResponse({
            "error": "Not enough available NFL players are loaded. Upload an NFL CSV with at least 1 QB, 2 RB, 3 WR, 1 TE, and 1 DST.",
            "position_counts": counts,
        }, status=400)

    slots = ("QB", "RB", "RB", "WR", "WR", "WR", "TE", "FLEX", "DST")
    eligible = {
        "QB": pools["QB"],
        "RB": pools["RB"],
        "WR": pools["WR"],
        "TE": pools["TE"],
        "FLEX": pools["RB"] + pools["WR"] + pools["TE"],
        "DST": pools["DST"],
    }

    best = None
    for _ in range(NFL_ATTEMPTS):
        lineup = []
        used_ids = set()
        for slot in slots:
            available = [p for p in eligible[slot] if p["id"] not in used_ids]
            if not available:
                break
            player = random.choice(available)
            lineup.append(player)
            used_ids.add(player["id"])
        if len(lineup) != len(slots):
            continue
        salary = sum(int(p["salary"] or 0) for p in lineup)
        if salary > 50000:
            continue
        projection = sum(float(p["projection"] or 0) for p in lineup)
        if best is None or projection > best[0]:
            best = (projection, lineup)

    if best is None:
        return JsonResponse({
            "error": "Could not build an NFL lineup under the $50,000 salary cap. Check player salaries and positions.",
            "position_counts": counts,
        }, status=400)
    return JsonResponse(_serialize_lineup(slots, best[1]))


@require_GET
def generate_nba_lines(request):
    """Generate an NBA lineup using each player's full multi-position eligibility."""
    players = [p for p in Player.objects.values(*PLAYER_FIELDS) if not _is_unavailable(p)]
    if not players:
        return JsonResponse({"error": "No available players are loaded. Upload an NBA salary CSV first."}, status=400)

    eligible = {
        slot: [p for p in players if _position_tokens(p["position"]) & positions]
        for slot, positions in NBA_SLOTS
    }
    missing = [slot for slot, _ in NBA_SLOTS if not eligible[slot]]
    if missing:
        return JsonResponse({
            "error": "The uploaded NBA player data has no eligible players for these roster slots.",
            "missing_slots": missing,
            "position_counts": {
                token: sum(token in _position_tokens(p["position"]) for p in players)
                for token in ("PG", "SG", "SF", "PF", "C")
            },
        }, status=400)

    slots = tuple(slot for slot, _ in NBA_SLOTS)
    lineup, visited = _find_best_lineup(slots, eligible)
    if lineup is None:
        return JsonResponse({
            "error": "No unique 8-player NBA lineup fits the $50,000 cap. Check salaries and player eligibility in the uploaded CSV.",
            "search_nodes": visited,
        }, status=400)
    return JsonResponse(_serialize_lineup(slots, lineup))


@login_required
def dope_dashboard(request):
    return render(request, "DopeInTheMornings.html")


@login_required
def nba_dashboard(request):
    return render(request, "NBA.html")
