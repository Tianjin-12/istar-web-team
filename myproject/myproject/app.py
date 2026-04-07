# myproject/apps.py
from django.apps import AppConfig


class MyprojectConfig(AppConfig):
    name = "myproject"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        pass
