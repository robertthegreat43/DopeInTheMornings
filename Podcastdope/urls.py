from django.contrib import admin, auth
from django.urls import path, include
from django.shortcuts import redirect
from django.shortcuts import redirect

def root_redirect(request):
    return redirect("register")


urlpatterns = [
    path('admin/', admin.site.urls),

    # Django auth URLs
    path("accounts/", include(("django.contrib.auth.urls", "auth"), namespace='accounts')),

    # FIRST PAGE → REGISTER
    path('', root_redirect),

    # DFS app
    path('', include('dfslineups.urls')),
]
