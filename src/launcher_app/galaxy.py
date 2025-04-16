"""Defines a class for interacting with a specified Galaxy server.

The server to connect to can be controlled via the GALAXY_URL setting.
The endpoint on the server through which to get a user's API key can be
controlled via the GALAXY_API_KEY_ENDPOINT setting.
The history name to use for all jobs can be controlled via the
GALAXY_HISTORY_NAME setting.
"""

import json
import logging
from time import sleep
from typing import Any, Dict, Optional

from bs4 import BeautifulSoup
from django.conf import settings
from nova.galaxy import Connection, Parameters, Tool, WorkState
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
            self.connection = Connection(settings.GALAXY_URL, self.auth_manager.get_galaxy_api_key())
            self._connect_to_galaxy()
            self.tools_to_check: Dict[str, str] = {}
            with self.connection.connect() as connection:
                store = connection.create_data_store(name=settings.GALAXY_HISTORY_NAME)
                store.persist()
                for tool in store.recover_tools():
                    if tool.get_status() == WorkState.RUNNING:
                        self.tools_to_check[tool.id] = tool.get_uid()

    def _connect_to_galaxy(self) -> None:
        try:
            with self.connection.connect() as connection:
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
        try:
            with open(settings.PROTOTYPE_TOOLS_PATH, "r") as file:
                tool_json = tool_json | json.load(file)
        except Exception:
            # Prototype tools may not exist depending on the deployment environment.
            # The file could also become mangled since anyone with access to the prototype branch can affect its
            # generation. Due to these reasons, I think it's appropriate to be very broad in the error handling.
            pass
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

    def launch_job(self, tool_id: str) -> str:
        with self.connection.connect() as connection:
            store = connection.create_data_store(name=settings.GALAXY_HISTORY_NAME)
            store.persist()
            tool = Tool(tool_id)
            params = Parameters()
            # This allows us to test the error monitoring at will on the test instance
            if tool_id == "neutrons_remote_command":
                params.add_input("command_mode|command", "fail")
            tool.run(data_store=store, params=params, wait=False)
            while not tool.get_uid():
                sleep(0.1)
            return tool.get_uid()

    def monitor_jobs(self, tool_ids: dict[str, str]) -> list:
        status_list = []
        with self.connection.connect() as connection:
            store = connection.create_data_store(name=settings.GALAXY_HISTORY_NAME)
            store.persist()
            self.tools_to_check.update(tool_ids)
            for tool_id, job_id in self.tools_to_check.items():
                tool = Tool("")
                tool.assign_id(new_id=job_id, data_store=store)
                try:
                    state = tool.get_status()
                    url = tool.get_url()
                    response = connection.galaxy_instance.make_get_request(url)
                    ready = response.status_code == 200
                    if state != WorkState.DELETED:
                        status_list.append(
                            {
                                "job_id": tool.get_uid(),
                                "tool_id": tool_id,
                                "state": state.value,
                                "url": url,
                                "url_ready": ready,
                            }
                        )
                except Exception:  # TODO: Might try to handle these better
                    continue
        return status_list

    def stop_job(self, tool_uid: str) -> None:
        with self.connection.connect() as connection:
            store = connection.create_data_store(name=settings.GALAXY_HISTORY_NAME)
            store.persist()
            tool = Tool("")
            tool.assign_id(new_id=tool_uid, data_store=store)
            tool.cancel()
