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


from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Player


@login_required
def nba_dashboard(request):
    return render(request, "NBA.html")


@login_required
def dope_dashboard(request):
    return render(request, "DopeInTheMornings.html")


@require_GET
def generate_nba_lines(request):

    players = list(
        Player.objects.values(
            "id",
            "name",
            "position",
            "team",
            "salary",
            "projection",
            "status"
        )
    )

    players = [
        p for p in players
        if (p.get("status") or "").upper()
        not in ["OUT", "IR", "INACTIVE"]
    ]

    if not players:
        return JsonResponse({
            "error": "No NBA players loaded."
        }, status=400)

    def has_pos(player, pos):
        position = (player.get("position") or "").upper()
        return pos in position

    pgs = [p for p in players if has_pos(p, "PG")]
    sgs = [p for p in players if has_pos(p, "SG")]
    sfs = [p for p in players if has_pos(p, "SF")]
    pfs = [p for p in players if has_pos(p, "PF")]
    centers = [p for p in players if has_pos(p, "C")]

    if not all([
        len(pgs),
        len(sgs),
        len(sfs),
        len(pfs),
        len(centers)
    ]):
        return JsonResponse({
            "error": "NBA positions are missing.",
            "counts": {
                "PG": len(pgs),
                "SG": len(sgs),
                "SF": len(sfs),
                "PF": len(pfs),
                "C": len(centers)
            }
        }, status=400)

    best_lineup = None
    best_projection = 0

    import random

    for _ in range(10000):

        try:

            lineup = {}

            lineup["PG"] = random.choice(pgs)
            lineup["SG"] = random.choice(sgs)
            lineup["SF"] = random.choice(sfs)
            lineup["PF"] = random.choice(pfs)
            lineup["C"] = random.choice(centers)

            used = {
                lineup["PG"]["id"],
                lineup["SG"]["id"],
                lineup["SF"]["id"],
                lineup["PF"]["id"],
                lineup["C"]["id"],
            }

            g_pool = [
                p for p in players
                if (
                    ("PG" in p["position"] or
                     "SG" in p["position"])
                    and p["id"] not in used
                )
            ]

            lineup["G"] = random.choice(g_pool)
            used.add(lineup["G"]["id"])

            f_pool = [
                p for p in players
                if (
                    ("SF" in p["position"] or
                     "PF" in p["position"])
                    and p["id"] not in used
                )
            ]

            lineup["F"] = random.choice(f_pool)
            used.add(lineup["F"]["id"])

            util_pool = [
                p for p in players
                if p["id"] not in used
            ]

            lineup["UTIL"] = random.choice(util_pool)

            total_salary = sum(
                int(p["salary"] or 0)
                for p in lineup.values()
            )

            if total_salary > 50000:
                continue

            total_projection = sum(
                float(p["projection"] or 0)
                for p in lineup.values()
            )

            if total_projection > best_projection:
                best_projection = total_projection
                best_lineup = lineup

        except Exception:
            continue

    if not best_lineup:
        return JsonResponse({
            "error":
            "Could not create NBA lineup under salary cap."
        }, status=400)

    return JsonResponse({

        "total_salary": sum(
            p["salary"]
            for p in best_lineup.values()
        ),

        "total_projection": round(
            sum(
                float(p["projection"] or 0)
                for p in best_lineup.values()
            ),
            2,
        ),

        "players": [

            {
                "slot": slot,
                "name": player["name"],
                "position": player["position"],
                "team": player["team"],
                "salary": player["salary"],
                "projection": player["projection"],
            }

            for slot, player
            in best_lineup.items()

        ]
    })
