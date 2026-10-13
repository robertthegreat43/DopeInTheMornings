from django.http import JsonResponse

from dfslineups.models import Player


def dfs_optimizer(request):
    players = Player.objects.prefetch_related('WeekPerformances').all()

    optimized = []

    for p in players:
        weeks = list(p.WeekPerformances.all())

        if len(weeks) < 2:
            trend = 0
        else:
            trend = weeks[-1].points - weeks[-2].points

        score = (p.projection * 0.7) + (trend * 0.3)

        optimized.append({
            "name": p.name,
            "position": p.position,
            "team": p.team,
            "salary": p.salary,
            "projection": p.projection,
            "trend": trend,
            "score": score
        })

    optimized.sort(key=lambda x: x["score"], reverse=True)

    return JsonResponse({"optimized": optimized})
