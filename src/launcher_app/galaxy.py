"""Defines a class for interacting with a specified Galaxy server.

The server to connect to can be controlled via the GALAXY_URL setting.
The endpoint on the server through which to get a user's API key can be
controlled via the GALAXY_API_KEY_ENDPOINT setting.
The history name to use for all jobs can be controlled via the
GALAXY_HISTORY_NAME setting.
"""

import json
import logging
from typing import Any, Dict, Optional

from bs4 import BeautifulSoup
from django.conf import settings
from nova.galaxy import Nova, Parameters, Tool, WorkState
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
            self.nova = Nova(settings.GALAXY_URL, self.auth_manager.get_galaxy_api_key())
            self._connect_to_galaxy()
            self.tools: Dict[str, Tool] = {}
            with self.nova.connect() as connection:
                store = connection.create_data_store(name=settings.GALAXY_HISTORY_NAME)
                store.persist()
                for tool in store.recover_tools():
                    if tool.get_status() == WorkState.RUNNING:
                        self.tools[tool.get_uid()] = tool

    def _connect_to_galaxy(self) -> None:
        try:
            with self.nova.connect() as connection:
                store = connection.create_data_store(name=settings.GALAXY_HISTORY_NAME)
                store.persist()
        except Exception as e:
            logger.error(f"Failed to connect to Galaxy: {e}")

            self.auth_manager.delete_galaxy_api_key()

            raise Exception(f"Failed to connect to Galaxy: {e}") from None

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
        with self.nova.connect() as connection:
            store = connection.create_data_store(name=settings.GALAXY_HISTORY_NAME)
            store.persist()
            tool = Tool(tool_id)
            tool.run(store=store, params=Parameters(), wait=False)
            self.tools[tool.get_uid()] = tool

    def monitor_jobs(self) -> list:
        self._connect_to_galaxy()
        status_list = []
        with self.nova.connect():
            for tool in self.tools.keys():
                try:
                    status_list.append(
                        {
                            "job_id": self.tools[tool].get_uid(),
                            "tool_id": self.tools[tool].id,
                            "state": self.tools[tool].get_status(),
                            "url": self.tools[tool].get_url(),
                        }
                    )
                except Exception:  # TODO: Might try to handle these better
                    continue
        return status_list

    def stop_job(self, tool_uid: str) -> None:
        self._connect_to_galaxy()
        with self.nova.connect():
            self.tools[tool_uid].cancel()
            self.tools.pop(tool_uid)
