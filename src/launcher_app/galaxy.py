"""Defines a class for interacting with a specified Galaxy server.

The server to connect to can be controlled via the GALAXY_URL setting.
The endpoint on the server through which to get a user's API key can be
controlled via the GALAXY_API_KEY_ENDPOINT setting.
The history name to use for all jobs can be controlled via the
GALAXY_HISTORY_NAME setting.
"""

import json
import logging
from typing import Any, Optional

from bioblend.galaxy import GalaxyInstance
from bs4 import BeautifulSoup
from django.conf import settings
from requests import get as requests_get

from .auth import AuthManager

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class GalaxyManager:
    """Manages and monitors Galaxy jobs.

    auth_manager is an instance of AuthManager that will be used to
    authenticate with Galaxy to get the user's API key.
    """

    def __init__(self, auth_manager: Optional[AuthManager] = None):
        """Init."""
        if auth_manager is not None:
            self.auth_manager = auth_manager
            self._connect_to_galaxy()

    def _connect_to_galaxy(self) -> None:
        try:
            self.galaxy_instance = GalaxyInstance(
                url=settings.GALAXY_URL,
                key=self.auth_manager.get_galaxy_api_key(),
            )
        except Exception as e:
            logger.error(f"Failed to connect to Galaxy: {e}")

            self.auth_manager.delete_galaxy_api_key()
            self.galaxy_instance = None  # type: ignore

            raise Exception(f"Failed to connect to Galaxy: {e}") from None

    def _get_history_id(self) -> str:
        histories = self.galaxy_instance.histories.get_histories(name=settings.GALAXY_HISTORY_NAME)
        if len(histories) > 0:
            return histories[0]["id"]

        result = self.galaxy_instance.histories.create_history(settings.GALAXY_HISTORY_NAME)
        return result["id"]

    def _parse_tool_help(self, tool_help: str) -> str:
        soup = BeautifulSoup(tool_help, "html.parser")

        # Grab only the first line of the help text.
        return soup.get_text().strip().split("\n")[0].strip()

    def get_tools(self) -> dict[str, dict[str, Any]]:
        # I retrieve the tools.json like this to avoid errors when running locally.
        with open(settings.NOVA_TOOLS_PATH, "r") as file:
            tool_json = json.load(file)
        tool_details = {}

        # Retrieve the tool name and help text from the Galaxy server.
        galaxy_tools = requests_get(f"{settings.GALAXY_URL}/api/tools?tool_help=true").json()
        for galaxy_category in galaxy_tools:
            for tool in galaxy_category.get("elems", []):
                tool_details[tool["id"]] = tool

        for key in tool_json:
            category = tool_json[key]
            for index, tool_id in enumerate(category.get("tools", [])):
                if tool_id in tool_details:
                    galaxy_tool = tool_details[tool_id]

                    category["tools"][index] = {
                        "id": tool_id,
                        "name": galaxy_tool["name"],
                        "description": self._parse_tool_help(galaxy_tool["help"]),
                    }

        return tool_json

    def launch_job(self, tool_id: str) -> None:
        self._connect_to_galaxy()
        self.galaxy_instance.tools.run_tool(self._get_history_id(), tool_id, {})

    def monitor_jobs(self) -> list:
        self._connect_to_galaxy()

        history_contents = self.galaxy_instance.histories.show_history(
            self._get_history_id(), contents=True, deleted=False, details="all"
        )
        job_list = []
        entry_points = self.galaxy_instance.make_get_request(f"{settings.GALAXY_URL}/api/entry_points?running=true")
        for dataset in history_contents:
            try:
                # dataset does not contain tool_id
                job_id = dataset["creating_job"]
                job_info = self.galaxy_instance.jobs.show_job(job_id)
                if job_info["state"] == "queued" or job_info["state"] == "running" or job_info["state"] == "error":
                    # Search entry points json for correct job listing and try
                    # to get the target url.
                    target = None
                    for ep in entry_points.json():
                        if ep["job_id"] == job_id:
                            target = ep.get("target", None)
                    if target:
                        target = f"{settings.GALAXY_URL}{target}"

                        job_list.append(
                            {
                                "job_id": job_id,
                                "tool_id": job_info["tool_id"],
                                "state": job_info["state"],
                                "url": target,
                            }
                        )
            except Exception:
                # Some unusual datasets will cause issues. However, We still
                # want to check other datasets.
                continue
        return job_list

    def stop_job(self, job_id: str) -> None:
        self._connect_to_galaxy()
        self.galaxy_instance.jobs.cancel_job(job_id)
