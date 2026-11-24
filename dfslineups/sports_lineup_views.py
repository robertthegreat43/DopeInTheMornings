from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from .models import MLBPlayer, TennisPlayer
from .sports_lineup_generators import (
    MLB_SLOTS,
    TENNIS_SLOTS,
    generate_mlb_lineup as build_mlb_lineup,
    generate_tennis_lineup as build_tennis_lineup,
    serialize_lineup,
)


@login_required
def tennis_dashboard(request):
    return render(request, "Tennis.html")


@require_GET
def generate_mlb_lineup(request):
    players = list(MLBPlayer.objects.values(
        "id", "name", "position", "team", "salary", "projection", "status"
    ))
    lineup, counts = build_mlb_lineup(players)
    if lineup is None:
        message = (
            "Not enough available MLB players are loaded. DraftKings MLB Classic requires "
            "2 P, 1 C, 1 1B, 1 2B, 1 3B, 1 SS, and 3 OF; also check the $50,000 cap "
            "and the five-player-per-team limit."
        )
        return JsonResponse({"error": message, "position_counts": counts}, status=400)
    return JsonResponse(serialize_lineup(MLB_SLOTS, lineup))


@require_GET
def generate_tennis_lineup(request):
    players = list(TennisPlayer.objects.values(
        "id", "name", "position", "team", "match_id", "salary", "projection", "status"
    ))
    lineup, counts = build_tennis_lineup(players)
    if lineup is None:
        return JsonResponse({
            "error": "Could not build a six-player tennis lineup under the $50,000 cap "
                     "and DraftKings limit of four players per match. Check the tennis player pool.",
            "player_count": counts["players"],
        }, status=400)
    return JsonResponse(serialize_lineup(TENNIS_SLOTS, lineup))
