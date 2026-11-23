import numpy as np
from django.http import JsonResponse
from django.shortcuts import render
from sklearn.linear_model import LinearRegression


def projections(request):
    """Display the score projection form and predict the next game score."""
    if request.method == "GET":
        return render(request, "projections.html")
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed."}, status=405)

    team_name = request.POST.get("team_name", "").strip()
    raw_game_count = request.POST.get("games_played", "")
    raw_scores = request.POST.getlist("scores")

    if not team_name or len(team_name) > 20:
        return JsonResponse({"error": "Enter a team name up to 20 characters."}, status=400)
    try:
        games_played = int(raw_game_count)
    except (TypeError, ValueError):
        return JsonResponse({"error": "Enter a valid number of games."}, status=400)
    if games_played < 1 or games_played > 7:
        return JsonResponse({"error": "Enter between 1 and 7 games."}, status=400)
    if len(raw_scores) != games_played:
        return JsonResponse({"error": "Enter one score for every game played."}, status=400)

    try:
        scores = [int(score) for score in raw_scores]
    except (TypeError, ValueError):
        return JsonResponse({"error": "Every score must be a whole number."}, status=400)
    if any(score < 0 for score in scores):
        return JsonResponse({"error": "Scores cannot be negative."}, status=400)

    game_numbers = np.arange(1, games_played + 1).reshape(-1, 1)
    model = LinearRegression()
    model.fit(game_numbers, np.asarray(scores))
    projection = round(float(model.predict([[games_played + 1]])[0]), 2)

    return JsonResponse({
        "team_name": team_name,
        "games_played": games_played,
        "scores": scores,
        "projection": projection,
    })

