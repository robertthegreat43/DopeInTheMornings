from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, User

from .models import DKSalaryFile, Player, WeekPerformance


class DfslineupsAdminSite(admin.AdminSite):
    site_title = "Dope In The Mornings"
    site_header = "Dope In The Mornings"
    index_title = "Dope In The Mornings"


admin_site = DfslineupsAdminSite(name="admin")


class WeekPerformanceInline(admin.TabularInline):
    model = WeekPerformance
    extra = 0
    max_num = 16
    verbose_name = "A player's performance for a given week"


@admin.register(Player, site=admin_site)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ("name", "position", "team", "projection")
    inlines = [WeekPerformanceInline]


@admin.register(WeekPerformance, site=admin_site)
class WeekPerformanceAdmin(admin.ModelAdmin):
    list_display = ("player", "week", "points")
    list_filter = ("week", "player")


@admin.register(DKSalaryFile, site=admin_site)
class DKSalaryFileAdmin(admin.ModelAdmin):
    list_display = ("uploaded_at", "file")


@admin.register(User, site=admin_site)
class CustomUserAdmin(UserAdmin):
    pass


@admin.register(Group, site=admin_site)
class CustomGroupAdmin(GroupAdmin):
    pass
