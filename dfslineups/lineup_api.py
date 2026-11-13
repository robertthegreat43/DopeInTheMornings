import csv
import random
import re
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from .models import DKSalaryFile


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
NFL_SLOTS = ("QB", "RB", "RB", "WR", "WR", "WR", "TE", "FLEX", "DST")
NFL_SALARY_CAP = 50000
NBA_SALARY_CAP = 50000
NFL_MIN_PROJECTION = 120
NFL_SIMULATIONS = 1_000_000

COLUMN_ALIASES = {
    "name": ("name", "player", "player name", "name + id"),
    "position": ("position", "roster position", "pos"),
    "team": ("teamabbrev", "team", "tm"),
    "salary": ("salary", "cost"),
    "projection": ("avgpointspergame", "fppg", "projection", "proj", "fantasy points per game", "fpts"),
}


def _position_tokens(position):
    tokens = set(re.findall(r"[A-Z]+", str(position or "").upper()))
    if "D" in tokens:
        tokens.add("DST")
    if "DEF" in tokens:
        tokens.add("DST")
    if "FORWARD" in tokens:
        tokens.update(("F", "SF"))
    if "CENTER" in tokens:
        tokens.add("C")
    return tokens


def _number(value, default=0.0):
    try:
        return float(str(value or "").replace(",", "").replace("$", "").strip())
    except (TypeError, ValueError):
        return default


def _csv_value(row, field):
    normalized = {str(key or "").replace("\ufeff", "").strip().casefold(): value for key, value in row.items()}
    for alias in COLUMN_ALIASES[field]:
        value = normalized.get(alias.casefold())
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _is_league_player(player, league):
    tokens = _position_tokens(player["position"])
    if league == "nfl":
        return bool(tokens & {"QB", "RB", "WR", "TE", "DST"})
    return bool(tokens & {"PG", "SG", "SF", "PF", "C", "F", "FORWARD", "CENTER"})


def _players_from_file(file_obj, league):
    players = []
    with file_obj.open("rb") as binary_file:
        import io

        text_file = io.TextIOWrapper(binary_file, encoding="utf-8-sig", newline="")
        try:
            reader = csv.DictReader(text_file)
            for row_number, row in enumerate(reader):
                name = _csv_value(row, "name")
                position = _csv_value(row, "position")
                salary = int(_number(_csv_value(row, "salary")))
                if not name or not position or salary <= 0:
                    continue
                player = {
                    "name": name,
                    "position": position,
                    "team": _csv_value(row, "team"),
                    "salary": salary,
                    "projection": _number(_csv_value(row, "projection")),
                    "_id": row_number,
                }
                if _is_league_player(player, league):
                    players.append(player)
        finally:
            # Keep ownership of the underlying storage file with its context manager.
            text_file.detach()
    return players


def _saved_csv_paths():
    paths = []
    for saved_file in DKSalaryFile.objects.order_by("-uploaded_at"):
        try:
            paths.append(saved_file.file)
        except (OSError, ValueError):
            continue
    if not paths:
        root = Path(settings.MEDIA_ROOT)
        if root.exists():
            paths.extend(sorted(root.rglob("*.csv"), key=lambda path: path.stat().st_mtime, reverse=True))
    return paths


def _load_players_from_saved_csv(league):
    for saved_file in _saved_csv_paths():
        try:
            players = _players_from_file(saved_file, league)
        except (OSError, UnicodeError, csv.Error, AttributeError):
            continue
        if players:
            return players
    return []


def _serialize_lineup(slots, lineup):
    serialized_players = []
    for slot, player in zip(slots, lineup):
        serialized_players.append({
            "slot": slot,
            "position": player["position"],
            "name": player["name"],
            "team": player["team"],
            "salary": player["salary"],
            "projection": round(player["projection"], 2),
        })
    return {
        "players": serialized_players,
        "total_salary": sum(player["salary"] for player in serialized_players),
        "total_projection": round(sum(player["projection"] for player in serialized_players), 2),
    }


def _search_nba_lineup(players, salary_cap=NBA_SALARY_CAP, max_nodes=200000):
    eligible = {
        slot: [p for p in players if _position_tokens(p["position"]) & positions]
        for slot, positions in NBA_SLOTS
    }
    missing = [slot for slot, _ in NBA_SLOTS if not eligible[slot]]
    if missing:
        return None, missing

    best = None
    nodes = 0

    def search(remaining, lineup, used_ids, salary, projection):
        nonlocal best, nodes
        if nodes >= max_nodes:
            return
        if not remaining:
            if best is None or projection > best[0]:
                best = (projection, lineup.copy())
            return

        # Search the most constrained open roster slot first; prioritize high projections.
        choices = []
        for slot, positions in remaining:
            candidates = [
                p for p in eligible[slot]
                if p["_id"] not in used_ids and salary + p["salary"] <= salary_cap
            ]
            choices.append((len(candidates), slot, positions, candidates))
        _, slot, _positions, candidates = min(choices, key=lambda item: item[0])
        if not candidates:
            return
        candidates.sort(key=lambda p: p["projection"], reverse=True)
        next_remaining = [item for item in remaining if item[0] != slot]
        for player in candidates:
            nodes += 1
            if nodes > max_nodes:
                break
            lineup[slot] = player
            used_ids.add(player["_id"])
            search(next_remaining, lineup, used_ids, salary + player["salary"], projection + player["projection"])
            used_ids.remove(player["_id"])
            del lineup[slot]

    search(list(NBA_SLOTS), {}, set(), 0, 0.0)
    if best is None:
        return None, ["A unique 8-player lineup under the $50,000 salary cap"]
    return [best[1][slot] for slot, _ in NBA_SLOTS], []


def _nba_position_tokens(position):
    tokens = _position_tokens(position)
    if "F" in tokens:
        tokens.update(("SF", "FORWARD"))
    return tokens


def _find_nba_lineup(players, salary_cap=NBA_SALARY_CAP, max_nodes=200000):
    # NBA eligibility normalization handles the common DK F-only and multi-position forms.
    normalized_players = []
    for player in players:
        player = dict(player)
        tokens = _nba_position_tokens(player["position"])
        player["position"] = "/".join(sorted(tokens))
        normalized_players.append(player)
    return _search_nba_lineup(normalized_players, salary_cap, max_nodes)


def _find_nfl_lineup(players, salary_cap=NFL_SALARY_CAP, min_projection=NFL_MIN_PROJECTION):
    pools = {
        position: [p for p in players if position in _position_tokens(p["position"])]
        for position in ("QB", "RB", "WR", "TE", "DST")
    }
    if not pools["QB"] or len(pools["RB"]) < 2 or len(pools["WR"]) < 3 or not pools["TE"] or not pools["DST"]:
        return None, "The saved NFL CSV is missing players needed for QB, 2 RB, 3 WR, TE, FLEX, and DST."
    flex_pool = pools["RB"] + pools["WR"] + pools["TE"]
    best = None

    # The requested million simulations improve projection quality. A deterministic
    # feasibility search below is used if sampling misses an otherwise valid lineup.
    for _ in range(NFL_SIMULATIONS):
        qb = random.choice(pools["QB"])
        rbs = random.sample(pools["RB"], 2)
        wrs = random.sample(pools["WR"], 3)
        te = random.choice(pools["TE"])
        dst = random.choice(pools["DST"])
        selected_ids = {p["_id"] for p in [qb, *rbs, *wrs, te, dst]}
        eligible_flex = [p for p in flex_pool if p["_id"] not in selected_ids]
        if not eligible_flex:
            continue
        flex = random.choice(eligible_flex)
        lineup = [qb, *rbs, *wrs, te, flex, dst]
        salary = sum(p["salary"] for p in lineup)
        if salary > salary_cap:
            continue
        projection = sum(p["projection"] for p in lineup)
        if projection >= min_projection and (best is None or projection > best[0]):
            best = (projection, lineup)

    if best:
        return best[1], None

    # Search by salary/projection for a valid lineup instead of failing just because
    # random sampling did not happen to draw one.
    slots = list(NFL_SLOTS)
    candidates = {slot: pools[slot] if slot != "FLEX" else flex_pool for slot in set(slots)}
    for values in candidates.values():
        values.sort(key=lambda p: (p["salary"], -p["projection"]))
    nodes = 0
    max_nodes = 1_000_000
    chosen = []
    used_ids = set()
    result = None

    def feasibility_search(index, salary, projection):
        nonlocal nodes, result
        if result is not None or nodes >= max_nodes:
            return
        if index == len(slots):
            if projection >= min_projection:
                result = chosen.copy()
            return
        remaining = slots[index:]
        if projection + sum(max(p["projection"] for p in candidates[slot]) for slot in remaining) < min_projection:
            return
        if salary + sum(min(p["salary"] for p in candidates[slot]) for slot in remaining) > salary_cap:
            return
        slot = slots[index]
        for player in candidates[slot]:
            nodes += 1
            if nodes >= max_nodes:
                break
            if player["_id"] in used_ids or salary + player["salary"] > salary_cap:
                continue
            chosen.append(player)
            used_ids.add(player["_id"])
            feasibility_search(index + 1, salary + player["salary"], projection + player["projection"])
            used_ids.remove(player["_id"])
            chosen.pop()
            if result is not None:
                return

    feasibility_search(0, 0, 0.0)
    if result:
        return result, None
    return None, "No unique NFL lineup met the $50,000 cap and 120-point projection minimum. Check CSV salaries/projections and position coverage."


@require_GET
def generate_nfl_lines(request):
    """Generate an NFL DraftKings lineup from the latest saved NFL salary CSV."""
    players = _load_players_from_saved_csv("nfl")
    if not players:
        return JsonResponse({"error": "No usable NFL players found in the saved DraftKings CSV files. Upload an NFL salary CSV first."}, status=400)
    lineup, error = _find_nfl_lineup(players)
    if error:
        return JsonResponse({"error": error}, status=400)
    return JsonResponse(_serialize_lineup(NFL_SLOTS, lineup))


@require_GET
def generate_nba_lines(request):
    """Generate an NBA DraftKings lineup from the latest saved NBA salary CSV."""
    players = _load_players_from_saved_csv("nba")
    if not players:
        return JsonResponse({"error": "No usable NBA players found in the saved DraftKings CSV files. Upload an NBA salary CSV first."}, status=400)
    lineup, issues = _find_nba_lineup(players)
    if issues:
        return JsonResponse({
            "error": "The saved NBA CSV cannot satisfy DraftKings NBA roster and salary rules.",
            "lineup_issues": issues,
        }, status=400)
    return JsonResponse(_serialize_lineup([slot for slot, _ in NBA_SLOTS], lineup))


@login_required
def dope_dashboard(request):
    return render(request, "DopeInTheMornings.html")


@login_required
def nba_dashboard(request):
    return render(request, "NBA.html")
