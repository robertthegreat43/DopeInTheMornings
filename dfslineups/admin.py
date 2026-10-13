from django.contrib import admin

# Register your models here.


# Register your models here.
from django.contrib import admin

from dfslineups.models import Player, WeekPerformance, DKSalaryFile
from django.contrib.admin import AdminSite




class DfslineupsAdminSite(AdminSite):
    title = "Dope In The Mornings"
    site_header = "Dope In The Mornings"
    index_title = "Dope In The Mornings"


class WeekPerformanceInline(admin.TabularInline):
    model = WeekPerformance
    max_num = 16
    verbose_name = 'A players performance for a given week'


class PlayerAdmin(admin.ModelAdmin):
    list_display = ('name', 'position', 'team', 'projection')
    inlines = [
        WeekPerformanceInline,
    ]

class WeekPerformanceAdmin(admin.ModelAdmin):
    list_display = ('player', 'week', 'points')
    list_filter = ('week', 'player')


admin.site.register(Player, PlayerAdmin)
admin.site.register(DKSalaryFile)
admin.site.register(WeekPerformance, WeekPerformanceAdmin)


