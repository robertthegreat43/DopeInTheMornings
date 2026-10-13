from django.urls import path, include
from rest_framework import routers
from dfslineups import views, api_view
from dfslineups.api_view import generatelines, get_week_performance, get_players
from dfslineups.views import user_profile, RegisterView, donations, get_position_breakdown

router = routers.DefaultRouter()
router.register(r'players', views.PlayerViewSet, basename='players')
router.register(r'players/qb', views.QuarterBackViewSet, basename='quarterbacks')
router.register(r'players/rb', views.RunningBackViewSet, basename='runningbacks')
router.register(r'players/wr', views.WideReceiverViewSet, basename='wide_receivers')
router.register(r'players/te', views.TightEndViewSet, basename='tight_ends')
router.register(r'players/dst', views.DefenseViewSet, basename='defenses')

urlpatterns = [

    #
    path("api/generatelines/", generatelines, name="generatelines"),

    # Router MUST be below custom endpoints
    path('', include(router.urls)),



    # Master optimized lineup page
    path("DopeInTheMornings/", views.dope_in_the_mornings, name="dope_in_the_mornings"),

    #admin-site urls
    path("accounts/profile/", user_profile, name="profile"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path(
        "password_change/", views.PasswordChangeView.as_view(), name="password_change"
    ),
    path(
        "password_change/done/",
        views.PasswordChangeDoneView.as_view(),
        name="password_change_done",
    ),
    path("password_reset/", views.PasswordResetView.as_view(), name="password_reset"),
    path(
        "password_reset/done/",
        views.PasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        views.PasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),





    # Other paths
    path('video-feed/', views.video_feed, name='video_feed'),
    path('nfl-ticker/', views.nfl_news_ticker, name='nfl_ticker'),
    path('podcast/', views.podcast_dashboard, name='podcast_dashboard'),
    path('upload_to_dk/', views.upload_to_dk_file, name='upload_to_dk'),
    path("upload_dk_csv_page/", views.upload_dk_csv_page, name="upload_dk_csv_page"),
    path("serialize_full_lineup/", views.serialize_full_lineup, name="serialize_full_lineup"),
    path("full_lineup/", views.full_lineup_page, name="full_lineup_page"),
    path("get_serialized_entries/", views.get_serialized_entries, name="get_serialized_entries"),
    path("view-full-lineups/", views.view_full_lineups),
    path("generate/lineups/", views.generate_optimal_lineups),
    path("stop_recording/", api_view.stop_recording),
    path("start_recording/", api_view.start_recording),
    path("register/", RegisterView.as_view(), name="register"),
    path("donations/", donations, name="donations"),
    path('week_performance/', get_week_performance, name='week_performance'),
    path('get_week_performance/', get_week_performance, name='get_week_performance'),
    path("get_players/", get_players, name="get_players"),
    path("get_position_breakdown/", get_position_breakdown, name="get_position_breakdown"),











    # Sports news API
    path("get_sports_news/", views.get_sports_news, name="get_sports_news"),








    # Optimized lineup engine
    path("get-serialized-entries/", views.get_serialized_entries, name="get_serialized_entries"),

    # Position pages
    path("qb/", views.qb_page, name="qb_page"),
    path("rb/", views.rb_page, name="rb_page"),
    path("wr/", views.wr_page, name="wr_page"),
    path("te/", views.te_page, name="te_page"),
    path("dst/", views.dst_page, name="dst_page"),
    path("flex/", views.flex_page, name="flex_page"),

    # Training endpoints
    path("train/qb/", views.train_qb, name="train_qb"),
    path("train/rb/", views.train_rb, name="train_rb"),
    path("train/wr/", views.train_wr, name="train_wr"),
    path("train/te/", views.train_te, name="train_te"),
    path("train/dst/", views.train_dst, name="train_dst"),
    path("train/flex/", views.train_flex, name="train_flex"),

    # Serialization endpoints
    path("serialize/qb/", views.serialize_qb, name="serialize_qb"),
    path("serialize/rb/", views.serialize_rb, name="serialize_rb"),
    path("serialize/wr/", views.serialize_wr, name="serialize_wr"),
    path("serialize/te/", views.serialize_te, name="serialize_te"),
    path("serialize/dst/", views.serialize_dst, name="serialize_dst"),
    path("serialize/flex/", views.serialize_flex, name="serialize_flex"),
]

