"""Manages fetching and processing system status data."""

from typing import Any, Dict, List

import requests
from django.conf import settings


class StatusManager:
    """Manages fetching and processing system status data."""

    def get_alerts(self) -> List[Dict[str, Any]]:
        response = requests.get(settings.ALERTS_URL, verify=False)
        raw_data = response.json()

        return self.process_alerts(raw_data)

    def get_targets(self) -> List[Dict[str, Any]]:
        response = requests.get(settings.TARGETS_URL, verify=False)
        raw_data = response.json()

        return self.process_targets(raw_data)

    def process_alerts(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        format = settings.ALERTS_FORMAT

        match format:
            case "prometheus":
                return self.process_prometheus_alerts(raw_data)
            case _:
                raise ValueError(f"Alert processing for format '{format}' not implemented.")

    def process_prometheus_alerts(self, raw_alerts: Dict[str, Any]) -> List[Dict[str, Any]]:
        processed_alerts = []
        for alert in raw_alerts.get("data", {}).get("alerts", []):
            annotations = alert.get("annotations", {})
            labels = alert.get("labels", {})
            alias = labels.get("alias", "")
            environment = labels.get("env", "")
            group = labels.get("nova_group", "")
            severity = labels.get("severity", "")
            subtitle = annotations.get("description", "")
            title = annotations.get("title", "")

            if environment in settings.ALERTS_ENVIRONMENTS:
                processed_alerts.append(
                    {
                        "alias": alias,
                        "environment": environment,
                        "group": group,
                        "severity": severity,
                        "subtitle": subtitle,
                        "title": title,
                    }
                )

        return processed_alerts

    def process_targets(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        format = settings.ALERTS_FORMAT

        match format:
            case "prometheus":
                return self.process_prometheus_targets(raw_data)
            case _:
                raise ValueError(f"Target processing for format '{format}' not implemented.")

    def process_prometheus_targets(self, raw_targets: Dict[str, Any]) -> List[Dict[str, Any]]:
        processed_targets = []
        for target in raw_targets.get("data", {}).get("activeTargets", []):
            labels = target.get("labels", {})
            alias = labels.get("alias", "")
            environment = labels.get("env", "")
            group = labels.get("nova_group", "")

            if environment in settings.ALERTS_ENVIRONMENTS:
                processed_targets.append({"alias": alias, "group": group})

        return processed_targets
