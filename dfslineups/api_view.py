

from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import FileResponse, Http404
import os

from dfslineups.models import Player, SerializedEntry, WeekPerformance
from .lineupgenrator import load_players_from_db, generate_dk_valid_lineup
from .serializers import PlayerSerializer, WeekPerformanceSerializer

from .stream import CameraController
import json
import re

camera = CameraController()
# ---------------------------------------------------------
# Load players from the DATABASE (correct version)
# ---------------------------------------------------------
def get_players_from_database():
    return list(Player.objects.all())


# ---------------------------------------------------------
# Generate optimized lineups
# ---------------------------------------------------------
@api_view(['GET'])
def get_week_performance(request):
    performances = WeekPerformance.objects.all().order_by('week')
    serializer = WeekPerformanceSerializer(performances, many=True)
    return Response(serializer.data)




@api_view(['GET'])
def get_players(request):
    players = Player.objects.all().order_by('name')
    data = [
        {
            "name": p.name,
            "position": p.position,
            "team": p.team,
            "projection": p.projection,
        }
        for p in players
    ]
    return Response(data)

# ---------------------------------------------------------
# Recording endpoints
# ---------------------------------------------------------
@api_view(['POST'])
def start_recording(request):
    filename = camera.start_recording()
    return Response({"status": "recording started", "file": filename})



@api_view(['POST'])
def stop_recording(request):
    camera.stop_recording()
    return Response({"status": "recording stopped"})



@api_view(['GET'])
def list_recordings(request):
    files = [f for f in os.listdir('.') if f.endswith('.mp4')]
    return Response({"videos": files})



@api_view(['GET'])
def download_video(request, filename):
    file_path = os.path.join(settings.BASE_DIR, filename)

    if not os.path.exists(file_path):
        raise Http404("Video file not found")

    return FileResponse(open(file_path, 'rb'), as_attachment=True)


@api_view(['GET'])
def generatelines(request):
    players = load_players_from_db()
    lineup = generate_dk_valid_lineup(players)

    if not lineup:
        return Response({"error": "Could not generate lineup"}, status=400)

    return Response({
        "players": [
            {
                "name": p["name"],
                "position": p["position"],
                "salary": p["salary"],
                "projection": p["projection"]
            }
            for p in lineup
        ],
        "total_salary": sum(p["salary"] for p in lineup),
        "total_projection": sum(p["projection"] for p in lineup)
    })


def convert_plain_text_to_json(text):
    lines = text.strip().split("\n")
    players = []
    total_points = 0

    for line in lines:
        line = line.strip()

        # Detect total points
        if line.lower().startswith("total"):
            match = re.search(r"(\d+(\.\d+)?)", line)
            if match:
                total_points = float(match.group(1))
            continue

        # Detect player lines: "QB Josh Allen 28.4"
        match = re.match(r"([A-Za-z]+)\s+(.+?)\s+(\d+(\.\d+)?)$", line)
        if match:
            pos = match.group(1)
            name = match.group(2)
            fpts = float(match.group(3))
            players.append({"pos": pos, "name": name, "fpts": fpts})

    return {
        "entry_type": "WIN",
        "players": players,
        "total_points": total_points
    }


def convert_json_to_unified(json_data):
    players = []
    total_points = json_data.get("total_points", 0)

    for pos, info in json_data.items():
        if pos == "total_points":
            continue
        if isinstance(info, dict) and "name" in info and "points" in info:
            players.append({
                "pos": pos,
                "name": info["name"],
                "fpts": info["points"]
            })

    return {
        "entry_type": "WIN",
        "players": players,
        "total_points": total_points
    }



@api_view(['POST'])
def submit_winning_lineup(request):
    raw = request.data.get("input")

    if raw is None:
        return Response({"error": "No input provided"}, status=400)

    # Case 1: already JSON/dict
    if isinstance(raw, dict):
        unified = convert_json_to_unified(raw)

    # Case 2: string
    elif isinstance(raw, str):
        raw = raw.strip()
        try:
            parsed = json.loads(raw)
            unified = convert_json_to_unified(parsed)
        except json.JSONDecodeError:
            unified = convert_plain_text_to_json(raw)

    else:
        return Response({"error": "Unsupported input type"}, status=400)

    SerializedEntry.objects.create(
        entry_type="WIN",
        position="FLEX",
        data=unified
    )

    return Response({"status": "saved", "data": unified})

@api_view(['GET'])
def all_players(request):
    players = Player.objects.all()
    serializer = PlayerSerializer(players, many=True)
    return Response(serializer.data)
