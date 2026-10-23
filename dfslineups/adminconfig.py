from django.contrib.admin.apps import AdminConfig


class DfslineupsAdminConfig(AdminConfig):
    default_site = "dfslineups.admin.DfslineupsAdminSite"
