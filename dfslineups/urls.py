from django.urls import include, path
from rest_framework import routers

from dfslineups import api_view, views
from dfslineups.lineup_api import (
    dope_dashboard,
    generate_nba_lines,
    generate_nfl_lines,
    nba_dashboard,
)
from dfslineups.views import RegisterView, donations, get_position_breakdown, user_profile


router = routers.DefaultRouter()
router.register(r"players", views.PlayerViewSet, basename="players")
router.register(r"players/qb", views.PlayerViewSet, basename="quarterbacks")
router.register(r"players/rb", views.PlayerViewSet, basename="runningbacks")
router.register(r"players/wr", views.PlayerViewSet, basename="wide_receivers")
router.register(r"players/te", views.PlayerViewSet, basename="tight_ends")
router.register(r"players/dst", views.PlayerViewSet, basename="defenses")
router.register(r"nba_players", views.PlayerViewSet, basename="nba_players")
router.register(r"players/pg", views.PlayerViewSet, basename="pointguards")
router.register(r"players/sg", views.PlayerViewSet, basename="shootingguards")
router.register(r"players/f", views.PlayerViewSet, basename="forwards")
router.register(r"players/pf", views.PlayerViewSet, basename="powerforwards")
router.register(r"players/center", views.PlayerViewSet, basename="centers")

urlpatterns = [
    # Frontend dashboards
    path("DopeInTheMornings/", dope_dashboard, name="dope_in_the_mornings"),
    path("nba_lines/", nba_dashboard, name="nba_lines"),

    # Separate NFL and NBA generators
    path("api/generatelines/", generate_nfl_lines, name="generatelines"),
    path("api/nba/generatelines/", generate_nba_lines, name="nba_generatelines"),

    # Router must be below custom endpoints
    path("", include(router.urls)),

    # Authentication/account pages
    path("accounts/profile/", user_profile, name="profile"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("password_change/", views.PasswordChangeView.as_view(), name="password_change"),
    path("password_change/done/", views.PasswordChangeDoneView.as_view(), name="password_change_done"),
    path("password_reset/", views.PasswordResetView.as_view(), name="password_reset"),
    path("password_reset/done/", views.PasswordResetDoneView.as_view(), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", views.PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("reset/done/", views.PasswordResetCompleteView.as_view(), name="password_reset_complete"),
    path("register/", RegisterView.as_view(), name="register"),
    path("donations/", donations, name="donations"),

    # Other app pages and APIs
    path("video-feed/", views.video_feed, name="video_feed"),
    path("nba-ticker/", views.nba_news_ticker, name="nba_ticker"),
    path("nfl-ticker/", views.nfl_news_ticker, name="nfl_ticker"),
    path("podcast/", views.podcast_dashboard, name="podcast_dashboard"),
    path("upload_to_dk/", views.upload_to_dk_file, name="upload_to_dk"),
    path("upload_dk_csv_page/", views.upload_dk_csv_page, name="upload_dk_csv_page"),
    path("serialize_full_lineup/", views.serialize_full_lineup, name="serialize_full_lineup"),
    path("full_lineup/", views.full_lineup_page, name="full_lineup_page"),
    path("get_serialized_entries/", views.get_serialized_entries, name="get_serialized_entries"),
    path("view-full-lineups/", views.view_full_lineups, name="view_full_lineups"),
    path("generate/lineups/", views.generate_optimal_lineups, name="generate_optimal_lineups"),
    path("stop_recording/", api_view.stop_recording, name="stop_recording"),
    path("start_recording/", api_view.start_recording, name="start_recording"),
    path("week_performance/", views.get_week_performance, name="week_performance"),
    path("get_week_performance/", views.get_week_performance, name="get_week_performance"),
    path("get_players/", api_view.get_players, name="get_players"),
    path("get_position_breakdown/", get_position_breakdown, name="get_position_breakdown"),
    path("get_sports_news/", views.get_sports_news, name="get_sports_news"),
    path("nba_news/", views.nba_news_ticker, name="nba_news"),

    # NFL pages
    path("qb/", views.qb_page, name="qb_page"),
    path("rb/", views.rb_page, name="rb_page"),
    path("wr/", views.wr_page, name="wr_page"),
    path("te/", views.te_page, name="te_page"),
    path("dst/", views.dst_page, name="dst_page"),
    path("flex/", views.flex_page, name="flex_page"),

    # NBA pages
    path("pg/", views.pg_page, name="pg_page"),
    path("sg/", views.sg_page, name="sg_page"),
    path("f/", views.f_page, name="f_page"),
    path("pf/", views.pf_page, name="pf_page"),
    path("center/", views.center_page, name="center_page"),

    # Training endpoints
    path("train/qb/", views.train_qb, name="train_qb"),
    path("train/rb/", views.train_rb, name="train_rb"),
    path("train/wr/", views.train_wr, name="train_wr"),
    path("train/te/", views.train_te, name="train_te"),
    path("train/dst/", views.train_dst, name="train_dst"),
    path("train/flex/", views.train_flex, name="train_flex"),
    path("train/pg/", views.train_pg, name="train_pg"),
    path("train/sg/", views.train_sg, name="train_sg"),
    path("train/f/", views.train_f, name="train_f"),
    path("train/pf/", views.train_pf, name="train_pf"),
    path("train/center/", views.train_center, name="train_center"),

    # Serialization endpoints
    path("serialize/qb/", views.serialize_qb, name="serialize_qb"),
    path("serialize/rb/", views.serialize_rb, name="serialize_rb"),
    path("serialize/wr/", views.serialize_wr, name="serialize_wr"),
    path("serialize/te/", views.serialize_te, name="serialize_te"),
    path("serialize/dst/", views.serialize_dst, name="serialize_dst"),
    path("serialize/flex/", views.serialize_flex, name="serialize_flex"),
    path("serialize/pg/", views.serialize_pg, name="serialize_pg"),
    path("serialize/sg/", views.serialize_sg, name="serialize_sg"),
    path("serialize/f/", views.serialize_f, name="serialize_f"),
    path("serialize/pf/", views.serialize_pf, name="serialize_pf"),
    path("serialize/center/", views.serialize_center, name="serialize_center"),
]
