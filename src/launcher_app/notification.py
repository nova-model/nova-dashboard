"""Defines a class for interacting with system notifications."""

from typing import Any, Dict

from .models import Notification


class NotificationManager:
    """Class to manage system notifications."""

    def get(self) -> Dict[str, Any]:
        notification = Notification.objects.first()
        if notification:
            return {"display": notification.display, "message": notification.message}

        return {}

    def set(self, data: Dict[str, Any]) -> None:
        notification = Notification.objects.first()
        if not notification:
            notification = Notification()

        if "display" in data:
            notification.display = data["display"]
        if "message" in data:
            notification.message = data["message"]

        notification.save()
