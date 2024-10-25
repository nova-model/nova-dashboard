"""Define the Django app configuration to allow our model to load properly."""

from django.apps import AppConfig


class LauncherConfig(AppConfig):
    """App config for Dashboard."""

    name = "src.launcher_app"
