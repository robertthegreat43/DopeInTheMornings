import json

import requests

from dfslineups.constants import POSITION_CHOICES, base_url
from dfslineups.models import Player, WeekPerformance


def get_all_player_data(maxweek: int):
    get_player_points(maxweek)
    fill_player_week_performances(maxweek)
    fill_total_points()


def get_player_points(maxweek: int = 1):
    for week in range(1, maxweek + 1):
        for position in POSITION_CHOICES:
            url = f"{base_url}{week}&position={position[0]}"
            response = requests.get(url)

            if response.status_code != 200:
                print(f"Failed to fetch week {week} position {position}")
                continue

            data = response.json()

            for player in data.get("players", []):
                # Create or update Player
                p, _ = Player.objects.get_or_create(name=player["name"])
                p.position = player["position"]
                p.team = player["teamAbbr"]
                p.save()

                # Build stats dict for analyzer
                stats = {
                    str(i): player["stats"].get(str(i), "0")
                    for i in range(91)
                }

                # Use YOUR analyzer instead of PyFL
                points = analyze_player_stats(
                    position=player["position"],
                    stats=stats,
                    week=week,
                    team=player["teamAbbr"]
                )

                # Create or update WeekPerformance
                WeekPerformance.objects.update_or_create(
                    player=p,
                    week=week,
                    defaults={"points": points},
                )


def fill_player_week_performances(maxweek: int = 1):
    for player in Player.objects.all():
        for week in range(1, maxweek + 1):
            WeekPerformance.objects.get_or_create(
                player=player,
                week=week,
                defaults={"points": 0},
            )


def fill_total_points():
    for player in Player.objects.all():
        total = sum(
            wp.points for wp in WeekPerformance.objects.filter(player=player)
        )
        player.total_points = total
        player.save()


def get_player_salaries():
    # temporarily making salaries 0 to work on frontend
    Player.objects.update(salary=0, opp="N/A", fppg=0)
