from django.contrib import admin
from django.urls import include, path
from django.shortcuts import redirect


def root_redirect(request):
    return redirect("register")


urlpatterns = [
    path('admin/', admin.site.urls),
    path("accounts/", include(("django.contrib.auth.urls", "auth"), namespace="accounts")),
    path('', root_redirect),
    path('', include('dfslineups.urls')),
]
