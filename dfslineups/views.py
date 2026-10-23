from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render
from django.views.generic import TemplateView

from .models import UserProfile

UserModel = get_user_model()


class RegisterView(TemplateView):
    template_name = "register.html"

    def get(self, request):
        form = UserCreationForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    "dsflineups_name067": user.username,
                    "dfslineups_password020": "",
                },
            )
            return redirect("login")
        return render(request, self.template_name, {"form": form})
