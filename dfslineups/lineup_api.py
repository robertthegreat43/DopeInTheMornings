import random

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from .lineupgenrator import generate_dk_valid_lineup, load_players_from_db
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


def _position_tokens(position):
    return {token.strip().upper() for token in (position or "").replace(",", "/").split("/")}


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
    """Use the existing NFL generator against the players loaded from the CSV."""
    players = load_players_from_db()
    lineup = generate_dk_valid_lineup(players)
    if not lineup:
        return JsonResponse({
            "error": (
                "Could not generate an NFL lineup from the uploaded player CSV. "
                "Check that it has enough QB, RB, WR, TE, and DST players with "
                "valid salary and projection values."
            )
        }, status=400)

    return JsonResponse({
        "players": [
            {
                "position": player["position"],
                "name": player["name"],
                "team": player.get("team"),
                "salary": int(player["salary"] or 0),
                "projection": float(player["projection"] or 0),
            }
            for player in lineup
        ],
        "total_salary": sum(int(player["salary"] or 0) for player in lineup),
        "total_projection": sum(float(player["projection"] or 0) for player in lineup),
    })


@require_GET
def generate_nba_lines(request):
    """Generate a DraftKings-style NBA lineup (PG, SG, SF, PF, C, G, F, UTIL)."""
    players = list(Player.objects.all())
    if not players:
        return JsonResponse({"error": "No players are loaded. Upload an NBA salary CSV first."}, status=400)

    eligible = {
        slot: [p for p in players if _position_tokens(p.position) & positions]
        for slot, positions in NBA_SLOTS
    }
    missing = [slot for slot, _ in NBA_SLOTS if not eligible[slot]]
    if missing:
        return JsonResponse({"error": "Not enough NBA position coverage to make a lineup.", "missing_slots": missing}, status=400)

    best = None
    slot_names = [slot for slot, _ in NBA_SLOTS]
    for _ in range(5000):
        lineup = []
        for slot, _positions in NBA_SLOTS:
            candidates = [p for p in eligible[slot] if p not in lineup]
            if not candidates:
                break
            lineup.append(random.choice(candidates))
        if len(lineup) != len(NBA_SLOTS):
            continue
        salary = sum(int(p.salary or 0) for p in lineup)
        if salary > 50000:
            continue
        projection = sum(float(p.projection or 0) for p in lineup)
        if best is None or projection > best[0]:
            best = (projection, lineup)

    if best is None:
        return JsonResponse({"error": "Could not build a unique NBA lineup under the $50,000 salary cap."}, status=400)

    return JsonResponse(_serialize_lineup(slot_names, best[1]))


@login_required
def dope_dashboard(request):
    return render(request, "DopeInTheMornings.html")


@login_required
def nba_dashboard(request):
    return render(request, "NBA.html")
