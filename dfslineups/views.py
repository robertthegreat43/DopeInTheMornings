import os
import csv
import json
import requests
import pandas as pd
from urllib.parse import urlsplit, urlunsplit

from django.conf import settings
from django.http import (
    StreamingHttpResponse,
    JsonResponse,
    HttpResponseRedirect,
    QueryDict,
)
from django.shortcuts import render, redirect, resolve_url
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, FormView
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth import (
    login as auth_login,
    logout as auth_logout,
    get_user_model,
)
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import PasswordChangeView, PasswordChangeDoneView
from django.utils.http import url_has_allowed_host_and_scheme, urlsafe_base64_decode
from django.utils.translation import gettext_lazy as _


from rest_framework import viewsets


from dfslineups.stream import CameraController
from dfslineups.nn_lineup_engine import NeuralLineupEngine
from dfslineups.serializers import (
    PlayerSerializer,
    LosingLineupSerializer,
    WinningLineupSerializer,
    FullLineupSerializer,
    WeekPerformanceSerializer,
)
from dfslineups.models import (
    DKSalaryFile,
    Player,
    SerializedEntry,
    FullLineup,
    WeekPerformance,
    UserProfile,
    DFSLineup,
)

UserModel = get_user_model()


def superuser_required(user):
    return user.is_superuser


def get_json(request):
    try:
        return json.loads(request.body)
    except:
        return None


# ------------------------------------------------------------
# DK CSV Upload Page
# ------------------------------------------------------------
@csrf_protect
@csrf_protect
def upload_to_dk_file(request):
    if request.method != "POST":
        return render(request, "upload_dk_file.html")

    uploaded_file = request.FILES.get("dk_file")
    if not uploaded_file:
        return render(request, "upload_dk_file.html", {"error": "No file selected."})

    dk_file = DKSalaryFile.objects.create(file=uploaded_file)
    dk_path = dk_file.file.path

    COLUMN_MAP = {
        "Name": ["Name", "Player", "Player Name"],
        "Position": ["Position", "Roster Position", "Pos"],
        "Team": ["TeamAbbrev", "Team", "Tm"],
        "Opponent": ["Opponent", "Opp", "Game Info", "GameInfo"],
        "Salary": ["Salary", "Cost"],
        "Projection": ["AvgPointsPerGame", "FPPG", "Projection", "Proj"],
        "Game": ["GameInfo", "Game", "Matchup"],
        "Status": ["Status", "Injury Status"],
        "Ownership": ["Ownership", "Own%", "Projected Ownership"],
        "DK_ID": ["ID", "PlayerID", "DK_ID"],
    }

    def get_value(row, key):
        for col in COLUMN_MAP[key]:
            if col in row and row[col] not in ("", None):
                return row[col]
        return None

    players_loaded = 0

    try:
        with open(dk_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                name = get_value(row, "Name")
                pos = get_value(row, "Position")

                if not name or not pos:
                    continue

                Player.objects.update_or_create(
                    name=name,
                    defaults={
                        "dk_id": get_value(row, "DK_ID"),
                        "position": pos,
                        "team": get_value(row, "Team"),
                        "opponent": get_value(row, "Opponent"),
                        "salary": float(get_value(row, "Salary") or 0),
                        "projection": float(get_value(row, "Projection") or 0),
                        "game": get_value(row, "Game"),
                        "status": get_value(row, "Status"),
                        "ownership": float(get_value(row, "Ownership") or 0),
                    }
                )

                players_loaded += 1

    except Exception as e:
        return render(request, "upload_dk_file.html", {"error": f"CSV parsing failed: {str(e)}"})

    # Generate weekly performance
    next_week = generate_week_performances_from_players()

    return render(request, "upload_dk_file.html", {
        "success": f"Loaded {players_loaded} players and added Week {next_week} performances."
    })


@login_required
def upload_dk_csv_page(request):
    return render(request, "upload_dk_csv.html")


# ------------------------------------------------------------
# Podcast Dashboard
# ------------------------------------------------------------

@user_passes_test(superuser_required)
def podcast_dashboard(request):
    players = Player.objects.all().order_by("-projection")[:50]
    return render(request, "podcast_dashboard.html", {"players": players})


# ------------------------------------------------------------
# Camera Streaming
# ------------------------------------------------------------

def video_feed(request):
    cam = CameraController()
    return StreamingHttpResponse(
        cam.stream(),
        content_type='multipart/x-mixed-replace; boundary=frame'
    )


# ------------------------------------------------------------
# NFL News Ticker
# ------------------------------------------------------------

def nfl_news_ticker(request):
    url = "https://tensorfeed.ai/api/sports/nfl/news?limit=50"

    try:
        data = requests.get(url, timeout=5).json()
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    articles = data.get("articles", [])

    ticker = [
        {
            "title": a.get("title"),
            "snippet": a.get("snippet"),
            "link": a.get("url"),
            "source": a.get("source")
        }
        for a in articles
    ]

    return JsonResponse({"ticker": ticker})


# ------------------------------------------------------------
# Optimal Lineups
# ------------------------------------------------------------

@csrf_exempt
def generate_optimal_lineups(request):
    if request.method == "GET":
        engine = NeuralLineupEngine()

        trained = engine.train()
        if not trained:
            return JsonResponse({"error": "Not enough training data"}, status=400)

        lineups = engine.generate_lineups(num_lineups=10)
        return JsonResponse({"lineups": lineups})

    return JsonResponse({"error": "Invalid method"}, status=405)


# ------------------------------------------------------------
# Full Lineup Page
# ------------------------------------------------------------

@login_required
def full_lineup_page(request):
    return render(request, "full_lineup_page.html")

# ------------------------------------------------------------
# Serialized Entries
# ------------------------------------------------------------

@login_required
def get_serialized_entries(request):
    entries = SerializedEntry.objects.all().order_by("-created_at")

    formatted = []
    for e in entries:
        formatted.append({
            "entry_type": e.entry_type,
            "position": e.position,
            "data": e.data,
            "created_at": e.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })

    return JsonResponse({"entries": formatted})


# ------------------------------------------------------------
# Week Performance
# ------------------------------------------------------------

@login_required
def get_week_performance(request):
    performances = WeekPerformance.objects.all().order_by("week")
    serializer = WeekPerformanceSerializer(performances, many=True)
    return JsonResponse(serializer.data, safe=False)

def get_next_week_number():
    existing_weeks = WeekPerformance.objects.values_list("week", flat=True).distinct()
    return max(existing_weeks) + 1 if existing_weeks else 1



def generate_week_performances_from_players():
    next_week = get_next_week_number()

    for player in Player.objects.all():
        WeekPerformance.objects.update_or_create(
            player=player,
            week=next_week,
            defaults={"points": float(player.projection or 0)}
        )

    return next_week



# ------------------------------------------------------------
# Position Pages
# ------------------------------------------------------------

@login_required
def qb_page(request):
    return render(request, "qb.html")

@login_required
def rb_page(request):
    return render(request, "rb.html")

@login_required
def wr_page(request):
    return render(request, "wr.html")

@login_required
def te_page(request):
    return render(request, "te.html")

@login_required
def dst_page(request):
    return render(request, "dst.html")

@login_required
def flex_page(request):
    return render(request, "flex.html")


# ------------------------------------------------------------
# Training Endpoints (WIN)
# ------------------------------------------------------------

@csrf_exempt
def train_qb(request):
    body = get_json(request)
    SerializedEntry.objects.create(entry_type="WIN", position="QB", data=body["lineup"])
    return JsonResponse({"status": "QB winning lineup saved"})

@csrf_exempt
def train_rb(request):
    body = get_json(request)
    SerializedEntry.objects.create(entry_type="WIN", position="RB", data=body["lineup"])
    return JsonResponse({"status": "RB winning lineup saved"})

@csrf_exempt
def train_wr(request):
    body = get_json(request)
    SerializedEntry.objects.create(entry_type="WIN", position="WR", data=body["lineup"])
    return JsonResponse({"status": "WR winning lineup saved"})

@csrf_exempt
def train_te(request):
    body = get_json(request)
    SerializedEntry.objects.create(entry_type="WIN", position="TE", data=body["lineup"])
    return JsonResponse({"status": "TE winning lineup saved"})

@csrf_exempt
def train_dst(request):
    body = get_json(request)
    SerializedEntry.objects.create(entry_type="WIN", position="DST", data=body["lineup"])
    return JsonResponse({"status": "DST winning lineup saved"})

@csrf_exempt
def train_flex(request):
    body = get_json(request)
    SerializedEntry.objects.create(entry_type="WIN", position="FLEX", data=body["lineup"])
    return JsonResponse({"status": "FLEX winning lineup saved"})


# ------------------------------------------------------------
# Serialization Endpoints (LOSS)
# ------------------------------------------------------------

@csrf_exempt
def serialize_qb(request):
    body = get_json(request)
    SerializedEntry.objects.create(entry_type="LOSS", position="QB", data=body["lineup"])
    return JsonResponse({"status": "QB lineup saved"})

@csrf_exempt
def serialize_rb(request):
    body = get_json(request)
    SerializedEntry.objects.create(entry_type="LOSS", position="RB", data=body["lineup"])
    return JsonResponse({"status": "RB lineup saved"})

@csrf_exempt
def serialize_wr(request):
    body = get_json(request)
    SerializedEntry.objects.create(entry_type="LOSS", position="WR", data=body["lineup"])
    return JsonResponse({"status": "WR lineup saved"})

@csrf_exempt
def serialize_te(request):
    body = get_json(request)
    SerializedEntry.objects.create(entry_type="LOSS", position="TE", data=body["lineup"])
    return JsonResponse({"status": "TE lineup saved"})

@csrf_exempt
def serialize_dst(request):
    body = get_json(request)
    SerializedEntry.objects.create(entry_type="LOSS", position="DST", data=body["lineup"])
    return JsonResponse({"status": "DST lineup saved"})

@csrf_exempt
def serialize_flex(request):
    body = get_json(request)
    SerializedEntry.objects.create(entry_type="LOSS", position="FLEX", data=body["lineup"])
    return JsonResponse({"status": "FLEX lineup saved"})


# ------------------------------------------------------------
# Full Lineup Serialization
# ------------------------------------------------------------

@csrf_exempt
def serialize_full_lineup(request):
    body = json.loads(request.body)
    serializer = FullLineupSerializer(data=body)

    if serializer.is_valid():
        serializer.save()
        return JsonResponse({"status": "Full lineup saved", "lineup": serializer.data})
    else:
        return JsonResponse(serializer.errors, status=400)


@csrf_exempt
def serialize_losing_lineup(request):
    body = json.loads(request.body)
    serializer = LosingLineupSerializer(data=body)

    if serializer.is_valid():
        serializer.save()
        return JsonResponse({"status": "Losing lineup saved"})
    else:
        return JsonResponse(serializer.errors, status=400)


@csrf_exempt
def serialize_winning_lineup(request):
    body = json.loads(request.body)
    serializer = WinningLineupSerializer(data=body)

    if serializer.is_valid():
        serializer.save()
        return JsonResponse({"status": "Winning lineup saved"})
    else:
        return JsonResponse(serializer.errors, status=400)


@csrf_exempt
def view_full_lineups(request):
    lineups = FullLineup.objects.all().order_by("-id")
    data = FullLineupSerializer(lineups, many=True).data
    return JsonResponse(data, safe=False)
# ------------------------------------------------------------
# Donations Page
# ------------------------------------------------------------

@login_required
def donations(request):
    return render(request, "Donations.html")


# ------------------------------------------------------------
# Dope In The Mornings Page
# ------------------------------------------------------------

@login_required
def dope_in_the_mornings(request):
    return render(request, "DopeInTheMornings.html")


# ------------------------------------------------------------
# User Profile
# ------------------------------------------------------------

@login_required
@csrf_exempt
def user_profile(request):
    user = request.user

    if request.method == "POST":
        user.username = request.POST.get("username")
        user.email = request.POST.get("email")
        user.save()

    return render(request, "user_profile.html", {"user_obj": user})


# ------------------------------------------------------------
# Register View
# ------------------------------------------------------------

class RegisterView(TemplateView):
    template_name = "register.html"

    def get(self, request):
        form = UserCreationForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("login")
        return render(request, self.template_name, {"form": form})


# ------------------------------------------------------------
# Custom Authentication Views (Your original ones)
# ------------------------------------------------------------

class RedirectURLMixin:
    next_page = None
    redirect_field_name = "next"
    success_url_allowed_hosts = set()

    def get_success_url(self):
        return self.get_redirect_url() or self.get_default_redirect_url()

    def get_redirect_url(self, request=None):
        if request is None:
            request = self.request
        redirect_to = request.POST.get(
            self.redirect_field_name, request.GET.get(self.redirect_field_name)
        )
        url_is_safe = url_has_allowed_host_and_scheme(
            url=redirect_to,
            allowed_hosts=self.get_success_url_allowed_hosts(request),
            require_https=request.is_secure(),
        )
        return redirect_to if url_is_safe else ""

    def get_success_url_allowed_hosts(self, request=None):
        if request is None:
            request = self.request
        return {request.get_host(), *self.success_url_allowed_hosts}

    def get_default_redirect_url(self):
        if self.next_page:
            return resolve_url(self.next_page)
        return resolve_url(settings.LOGIN_REDIRECT_URL)


@method_decorator(
    [sensitive_post_parameters(), csrf_protect, never_cache],
    name="dispatch",
)
class LoginView(RedirectURLMixin, FormView):
    form_class = AuthenticationForm
    template_name = "login.html"
    redirect_authenticated_user = False
    extra_context = None

    def dispatch(self, request, *args, **kwargs):
        if self.redirect_authenticated_user and self.request.user.is_authenticated:
            redirect_to = self.get_success_url()
            return HttpResponseRedirect(redirect_to)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        auth_login(self.request, form.get_user())
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_site = get_current_site(self.request)
        context.update(
            {
                self.redirect_field_name: self.get_redirect_url(),
                "site": current_site,
                "site_name": current_site.name,
                **(self.extra_context or {}),
            }
        )
        return context


class LogoutView(RedirectURLMixin, TemplateView):
    http_method_names = ["post", "options"]
    template_name = "logged_out.html"
    extra_context = None

    def post(self, request, *args, **kwargs):
        auth_logout(request)
        redirect_to = self.get_success_url()
        return HttpResponseRedirect(redirect_to)

    def get_default_redirect_url(self):
        if self.next_page:
            return resolve_url(self.next_page)
        return resolve_url(settings.LOGOUT_REDIRECT_URL)


# ------------------------------------------------------------
# Password Reset Views (Your original ones)
# ------------------------------------------------------------

class PasswordContextMixin:
    extra_context = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"title": self.title, **(self.extra_context or {})})
        return context


@method_decorator([csrf_protect], name="dispatch")
class PasswordResetView(PasswordContextMixin, FormView):
    form_class = PasswordResetForm
    template_name = "password_reset_form.html"
    email_template_name = "password_reset_email.html"
    subject_template_name = "password_reset_subject.txt"
    success_url = "password_reset_done"
    title = _("Password reset")
    token_generator = default_token_generator

    def form_valid(self, form):
        opts = {
            "use_https": self.request.is_secure(),
            "token_generator": self.token_generator,
            "from_email": None,
            "email_template_name": self.email_template_name,
            "subject_template_name": self.subject_template_name,
            "request": self.request,
        }
        form.save(**opts)
        return super().form_valid(form)


class PasswordResetDoneView(PasswordContextMixin, TemplateView):
    template_name = "password_reset_done.html"
    title = _("Password reset sent")


# ------------------------------------------------------------
# FIXED PasswordResetConfirmView
# ------------------------------------------------------------

@method_decorator([sensitive_post_parameters(), never_cache], name="dispatch")
class PasswordResetConfirmView(PasswordContextMixin, FormView):
    form_class = SetPasswordForm
    template_name = "password_reset_confirm.html"
    success_url = "password_reset_complete"
    title = _("Enter new password")
    token_generator = default_token_generator

    def dispatch(self, request, *args, **kwargs):
        self.validlink = False
        self.user = None

        uidb64 = kwargs.get("uidb64")
        token = kwargs.get("token")

        # Decode the user ID
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            self.user = UserModel._default_manager.get(pk=uid)
        except (TypeError, ValueError, OverflowError, UserModel.DoesNotExist):
            self.user = None

# ------------------------------------------------------------
# DRF ViewSets for Players and Positions
# ------------------------------------------------------------

class PlayerViewSet(viewsets.ModelViewSet):
    queryset = Player.objects.all().order_by('-projection')
    serializer_class = PlayerSerializer


class QuarterBackViewSet(viewsets.ModelViewSet):
    queryset = Player.objects.filter(position='QB').order_by('-projection')
    serializer_class = PlayerSerializer


class RunningBackViewSet(viewsets.ModelViewSet):
    queryset = Player.objects.filter(position='RB').order_by('-projection')
    serializer_class = PlayerSerializer


class WideReceiverViewSet(viewsets.ModelViewSet):
    queryset = Player.objects.filter(position='WR').order_by('-projection')
    serializer_class = PlayerSerializer


class TightEndViewSet(viewsets.ModelViewSet):
    queryset = Player.objects.filter(position='TE').order_by('-projection')
    serializer_class = PlayerSerializer


class DefenseViewSet(viewsets.ModelViewSet):
    queryset = Player.objects.filter(position='DST').order_by('-projection')
    serializer_class = PlayerSerializer

# ------------------------------------------------------------
# Password Change Views (Built‑in, as you selected)
# ------------------------------------------------------------

class CustomPasswordChangeView(PasswordChangeView):
    template_name = "password_change_form.html"
    success_url = "/password_change/done/"


class CustomPasswordChangeDoneView(PasswordChangeDoneView):
    template_name = "password_change_done.html"

class PasswordResetCompleteView(PasswordContextMixin, TemplateView):
    template_name = "password_reset_complete.html"
    title = _("Password reset complete")


import requests
from django.http import JsonResponse

def get_sports_news(request):
    """
    Fetch NFL sports news from TensorFeed and return clean JSON.
    """

    url = "https://tensorfeed.ai/api/sports/nfl/news?limit=50"

    try:
        response = requests.get(url, timeout=5)
        data = response.json()
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    articles = data.get("articles", [])

    formatted_news = []
    for a in articles:
        formatted_news.append({
            "title": a.get("title", "N/A"),
            "source": a.get("source", "Unknown"),
            "snippet": a.get("snippet", ""),
            "url": a.get("url", "#")
        })

    return JsonResponse({"news": formatted_news})




def generate_week_performances_from_players():
    """
    Create or update WeekPerformance rows for each Player
    using the Player.week and Player.projection fields.
    Does NOT modify Player objects.
    """
    for player in Player.objects.all():
        # DK CSV gives us the slate week
        week_number = player.week or 1

        WeekPerformance.objects.update_or_create(
            player=player,
            week=week_number,
            defaults={
                "points": int(player.projection or 0)
            }
        )
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Player

@api_view(['GET'])
def get_position_breakdown(request):
    players = Player.objects.all()

    # Build dictionary grouped by position
    breakdown = {}

    for p in players:
        pos = p.position or "Unknown"

        if pos not in breakdown:
            breakdown[pos] = {
                "count": 0,
                "total_projection": 0,
                "highest_projection": 0,
                "highest_player": None,
                "lowest_projection": None,
                "lowest_player": None,
            }

        # Update counts
        breakdown[pos]["count"] += 1
        breakdown[pos]["total_projection"] += (p.projection or 0)

        # Highest projection
        if (p.projection or 0) > breakdown[pos]["highest_projection"]:
            breakdown[pos]["highest_projection"] = p.projection or 0
            breakdown[pos]["highest_player"] = p.name

        # Lowest projection
        if breakdown[pos]["lowest_projection"] is None or (p.projection or 0) < breakdown[pos]["lowest_projection"]:
            breakdown[pos]["lowest_projection"] = p.projection or 0
            breakdown[pos]["lowest_player"] = p.name

    # Final formatting
    result = []
    for pos, stats in breakdown.items():
        avg_projection = stats["total_projection"] / stats["count"] if stats["count"] > 0 else 0

        result.append({
            "position": pos,
            "count": stats["count"],
            "avg_projection": round(avg_projection, 2),
            "highest_projection": round(stats["highest_projection"], 2),
            "highest_player": stats["highest_player"],
            "lowest_projection": round(stats["lowest_projection"], 2),
            "lowest_player": stats["lowest_player"],
        })

    return Response(result)
