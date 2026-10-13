import json

from django.http import JsonResponse
from dfslineups.nn_lineup_engine import NeuralLineupEngine
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def generate_optimal_lineups(request):
    """
    Generate optimized DFS lineups using the NeuralLineupEngine.
    Supports GET and POST.
    """
    engine = NeuralLineupEngine()

    # Optional: allow POST to specify number of lineups or salary cap
    if request.method == "POST":
        try:
            body = json.loads(request.body)
        except:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        num_lineups = body.get("num_lineups", 10)
        salary_cap = body.get("salary_cap", 50000)
    else:
        num_lineups = 10
        salary_cap = 50000

    # Train model if needed
    trained = engine.train()
    if not trained:
        return JsonResponse({
            "error": "Not enough training data to train the model."
        }, status=400)

    # Generate lineups
    lineups = engine.generate_lineups(
        salary_cap=salary_cap,
        num_lineups=num_lineups,
        samples=300  # number of random candidate lineups to evaluate
    )

    if not lineups:
        return JsonResponse({
            "error": "Unable to generate lineups. Check player database."
        }, status=400)

    return JsonResponse({"lineups": lineups}, safe=False)


