import random

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from .lineupgenrator import (
    generate_dk_valid_lineup,
    load_players_from_db,
    nfl_position_issues,
    position_tokens,
)
from .models import Player


NBA_SLOTS = (
    ("PG", {"PG"}),
    ("SG", {"SG"}),
    ("SF", {"SF", "F", "FORWARD"}),
    ("PF", {"PF"}),
    ("C", {"C", "CENTER"}),
    ("G", {"PG", "SG"}),
    ("F", {"SF", "F", "FORWARD", "PF"}),
    ("UTIL", {"PG", "SG", "SF", "F", "FORWARD", "PF", "C", "CENTER"}),
)


def _serialize_lineup(slots, lineup):
    players = []
    for slot, player in zip(slots, lineup):
        players.append({
            "slot": slot,
            "position": player.position,
            "name": player.name,
            "team": player.team,
            "salary": int(player.salary or 0),
            "projection": float(player.projection or 0),
        })
    return {
        "players": players,
        "total_salary": sum(player["salary"] for player in players),
        "total_projection": round(sum(player["projection"] for player in players), 2),
    }


@require_GET
def generate_nfl_lines(request):
    """Use the uploaded NFL CSV pool and enforce DraftKings roster/salary rules."""
    players = load_players_from_db()
    issues = nfl_position_issues(players)
    if issues:
        return JsonResponse({
            "error": "The uploaded player pool does not meet the DraftKings NFL roster requirements.",
            "position_issues": issues,
        }, status=400)

    lineup = generate_dk_valid_lineup(players)
    if not lineup:
        return JsonResponse({
            "error": "No valid NFL lineup fits the $50,000 DraftKings salary cap.",
        }, status=400)

    return JsonResponse({
        "players": [
            {
                "position": player["position"],
                "name": player["name"],
                "team": player.get("team"),
                "salary": int(player.get("salary") or 0),
                "projection": float(player.get("projection") or 0),
            }
            for player in lineup
        ],
        "total_salary": sum(int(player.get("salary") or 0) for player in lineup),
        "total_projection": round(
            sum(float(player.get("projection") or 0) for player in lineup), 2
        ),
    })


def _nba_position_tokens(position):
    tokens = position_tokens(position)
    if "FORWARD" in tokens:
        tokens.add("F")
        tokens.add("SF")
    if "CENTER" in tokens:
        tokens.add("C")
    return tokens


def _find_nba_lineup(players, salary_cap=50000, max_nodes=4000):
    """Find a unique-player NBA DK lineup with exact slot eligibility and cap.

    The node limit keeps this request bounded under Gunicorn. The previous
    exhaustive search could explore a combinatorial number of lineups and get
    killed by Gunicorn's request timeout before returning a response.
    """
    eligible_by_slot = {
        slot: [player for player in players
               if _nba_position_tokens(player.position) & eligible_positions]
        for slot, eligible_positions in NBA_SLOTS
    }
    missing = [slot for slot, _ in NBA_SLOTS if not eligible_by_slot[slot]]
    if missing:
        return None, missing

    # Cache numeric fields once rather than converting model values at each node.
    salaries = {player.pk: int(player.salary or 0) for player in players}
    projections = {player.pk: float(player.projection or 0) for player in players}
    best_assignment = None
    best_projection = float("-inf")
    nodes = 0

    def search(remaining, assignment, used, salary, projection):
        nonlocal best_assignment, best_projection, nodes
        if nodes >= max_nodes:
            return
        if not remaining:
            if projection > best_projection:
                best_projection = projection
                best_assignment = assignment.copy()
            return

        # Choose the slot with the fewest currently eligible players first.
        options = []
        for slot, _eligible_positions in remaining:
            candidates = [
                player for player in eligible_by_slot[slot]
                if player.pk not in used
                and salary + salaries[player.pk] <= salary_cap
            ]
            options.append((len(candidates), slot, candidates))
        _, slot, candidates = min(options, key=lambda item: item[0])
        if not candidates:
            return

        candidates.sort(key=lambda player: projections[player.pk], reverse=True)
        next_remaining = [item for item in remaining if item[0] != slot]
        for player in candidates:
            nodes += 1
            assignment[slot] = player
            used.add(player.pk)
            search(
                next_remaining,
                assignment,
                used,
                salary + salaries[player.pk],
                projection + projections[player.pk],
            )
            used.remove(player.pk)
            del assignment[slot]
            if nodes >= max_nodes:
                break

    search(list(NBA_SLOTS), {}, set(), 0, 0.0)
    if best_assignment is None:
        return None, ["A unique 8-player lineup under the $50,000 salary cap"]
    return [best_assignment[slot] for slot, _ in NBA_SLOTS], []


@require_GET
def generate_nba_lines(request):
    """Generate an NBA DraftKings lineup using the uploaded NBA CSV players."""
    players = list(Player.objects.all())
    if not players:
        return JsonResponse({"error": "No players are loaded. Upload an NBA salary CSV first."}, status=400)

    lineup, issues = _find_nba_lineup(players)
    if issues:
        return JsonResponse({
            "error": "The uploaded player pool cannot satisfy DraftKings NBA roster and salary rules.",
            "lineup_issues": issues,
        }, status=400)

    slots = [slot for slot, _ in NBA_SLOTS]
    return JsonResponse(_serialize_lineup(slots, lineup))


@login_required
def dope_dashboard(request):
    return render(request, "DopeInTheMornings.html")


@login_required
def nba_dashboard(request):
    return render(request, "NBA.html")
