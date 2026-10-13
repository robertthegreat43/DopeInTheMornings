import os
import django
import random

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Podcastdope.dev")
django.setup()

from dfslineups.models import Player


def load_players_from_db():
    return list(Player.objects.all().values(
        "name", "position", "team", "salary", "projection"
    ))


def has_pos(player, pos):
    return pos in player["position"]

def generate_dk_valid_lineup(players):
    # Position pools
    qbs = [p for p in players if has_pos(p, "QB")]
    rbs = [p for p in players if has_pos(p, "RB")]
    wrs = [p for p in players if has_pos(p, "WR")]
    tes = [p for p in players if has_pos(p, "TE")]
    dsts = [p for p in players if has_pos(p, "DST")]

    flex_pool = rbs + wrs + tes  # FLEX cannot be QB o
    # r DST

    # Safety checks
    if len(qbs) < 2 or len(rbs) < 2 or len(wrs) < 3 or len(tes) < 1 or len(dsts) < 1:
        print("ERROR: Not enough players for DK rules.")
        return None

    # Try generating until salary cap AND projection rules are valid
    for _ in range(100000):  # try up to 1000 times
        qb = random.choice(qbs)
        rb1, rb2 = random.sample(rbs, 2)
        wr1, wr2, wr3 = random.sample(wrs, 3)
        te = random.choice(tes)
        dst = random.choice(dsts)

        # FLEX must not duplicate any player
        flex_candidates = [p for p in flex_pool if p not in [rb1, rb2, wr1, wr2, wr3, te]]
        if not flex_candidates:
            continue

        flex = random.choice(flex_candidates)

        lineup = [qb, rb1, rb2, wr1, wr2, wr3, te, flex, dst]

        total_salary = sum(p["salary"] for p in lineup)
        total_proj = sum(p["projection"] for p in lineup)

        # DK rules:
        if total_salary <= 50000 and total_proj >= 120 :
            return lineup

    print("Could not generate DK-valid lineup within salary cap + projection ≥ 200.")
    return None





def print_lineup(lineup, number):
    print(f"\n================ DK LINEUP {number} ================")
    total_salary = sum(p["salary"] for p in lineup)
    total_proj = sum(p["projection"] for p in lineup)

    for p in lineup:
        print(f"{p['position']:8}  {p['name']:25}  ${p['salary']:5}  proj={p['projection']}")

    print("-----------------------------------------------")
    print("Total Salary:", total_salary)
    print("Total Projection:", total_proj)
    print("===============================================\n")


if __name__ == "__main__":
    players = load_players_from_db()
    print("Loaded", len(players), "players from database.")

    for i in range(1, 6):
        lineup = generate_dk_valid_lineup(players)
        if lineup:
            print_lineup(lineup, i)
