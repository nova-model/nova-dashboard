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
from nova.galaxy import Connection, Parameters, Tool
from requests import get as requests_get

from .auth import AuthManager

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


TERMINAL_STATES = ["deleted", "deleting", "error", "ok"]
NONTERMINAL_STATES = ["deleted_new", "failed", "new", "paused", "queued", "resubmitted", "running", "upload", "waiting"]


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
            with self.connection.connect() as connection:
                connection.create_data_store(name=settings.GALAXY_HISTORY_NAME)

    def _handle_galaxy_failure(self, exception: Exception) -> None:
        logger.error(f"Failed to connect to Galaxy: {exception}")

        self.auth_manager.delete_galaxy_api_key()

        raise Exception(f"Failed to connect to Galaxy: {exception}") from None

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
                prototype_tool_json = json.load(file)
        except Exception:
            # Prototype tools may not exist depending on the deployment environment.
            # The file could also become mangled since anyone with access to the prototype branch can affect its
            # generation. Due to these reasons, I think it's appropriate to be very broad in the error handling.
            prototype_tool_json = {}
        tool_details = {}
        # Retrieve the tool name and help text from the Galaxy server.
        galaxy_tools = requests_get(f"{settings.GALAXY_URL}/api/tools?tool_help=true").json()
        for galaxy_category in galaxy_tools:
            for tool in galaxy_category.get("elems", []):
                tool_details[tool["id"]] = tool

        for key, id in prototype_tool_json:
            if key not in tool_json:
                key = "misc"

            category = tool_json[key]
            if "prototype_tools" not in category:
                category["prototype_tools"] = []
            category["prototype_tools"].append(id)

        for key in tool_json:
            category = tool_json[key]
            for index, tool_id in enumerate(category.get("tools", [])):
                if tool_id in tool_details:
                    galaxy_tool = tool_details[tool_id]

                    category["tools"][index] = {
                        "id": tool_id,
                        "name": galaxy_tool["name"],
                        "description": self._parse_tool_help(galaxy_tool["help"]),
                        "version": galaxy_tool["version"],
                    }
            for index, tool_id in enumerate(category.get("prototype_tools", [])):
                if tool_id in tool_details:
                    galaxy_tool = tool_details[tool_id]

                    category["prototype_tools"][index] = {
                        "id": tool_id,
                        "name": galaxy_tool["name"],
                        "description": self._parse_tool_help(galaxy_tool["help"]),
                        "version": galaxy_tool["version"],
                    }

        return tool_json

    def ingest_file(self, connection: Connection, file_path: str) -> Optional[str]:
        file_store = connection.create_data_store(name=f"{settings.GALAXY_HISTORY_NAME}_data")
        load_data = Tool("neutrons_register")
        load_params = Parameters()
        load_params.add_input("series_0|input", file_path)
        outputs = load_data.run(file_store, load_params)

        try:
            return outputs.data[0].id
        except Exception:
            return None

    def launch_job(self, tool_id: str, inputs: dict[str, str]) -> str:
        with self.connection.connect() as connection:
            if inputs:
                store = connection.create_data_store(name=f"{settings.GALAXY_HISTORY_NAME}_datafile_tools")
            else:
                store = connection.create_data_store(name=settings.GALAXY_HISTORY_NAME)

            tool = Tool(tool_id)

            launch_params = Parameters()
            for key, value in inputs.items():
                if value.startswith("file_"):
                    # File will be ingested and contents will be passed to the tool.
                    id = self.ingest_file(connection, value)
                    if id is None:
                        raise ValueError(
                            f"File for parameter '{key}' failed to register to Galaxy. "
                            "The filepath is likely malformed or nonexistent."
                        )
                    launch_params.add_input(key, {"src": "hda", "id": id})
                else:
                    launch_params.add_input(key, value)

            # This allows us to test the error monitoring at will on the test instance
            if tool_id == "neutrons_remote_command":
                launch_params.add_input("command_mode|command", "fail")

            tool.run(data_store=store, params=launch_params, wait=False)

            while not tool.get_uid():
                sleep(0.1)
            return tool.get_uid()

    def monitor_jobs(self, tool_ids: Dict[str, str]) -> list:
        status_list = []
        try:
            with self.connection.connect() as connection:
                store = connection.create_data_store(name=settings.GALAXY_HISTORY_NAME)
                datafile_tools_store = connection.create_data_store(
                    name=f"{settings.GALAXY_HISTORY_NAME}_datafile_tools"
                )

                jobs = connection.galaxy_instance.jobs.get_jobs(history_id=store.history_id, state=NONTERMINAL_STATES)
                datafile_jobs = connection.galaxy_instance.jobs.get_jobs(
                    history_id=datafile_tools_store.history_id, state=NONTERMINAL_STATES
                )
                last_terminal_jobs = connection.galaxy_instance.jobs.get_jobs(
                    history_id=store.history_id,
                    limit=5,  # There are a lot of these, and we are only interested in the most recent ones.
                    order_by="create_time",
                    state=TERMINAL_STATES,
                )
                # We only want to show terminal jobs if the dashboard is already aware of them. If the user refreshes
                # the page after a job failed, then we don't want to display the error anymore.
                if last_terminal_jobs:
                    for _, known_job_id in tool_ids.items():
                        for job in last_terminal_jobs:
                            if job["id"] == known_job_id:
                                jobs.append(job)

                for job in datafile_jobs:
                    job["is_datafile_tool"] = True
                    jobs.append(job)

                for job in jobs:
                    tool = Tool("")
                    tool.assign_id(new_id=job["id"], data_store=store)
                    try:
                        state = job["state"]
                        url = tool.get_url(max_tries=1)
                        if url:
                            response = connection.galaxy_instance.make_get_request(url)
                            ready = (
                                response.status_code == 200
                                and "Proxy target missing"
                                not in response.text  # Avoid the proxy target missing page appearing
                                and "Javascript Required for Galaxy"
                                not in response.text  # Avoid the Galaxy homepage appearing
                            )
                        else:
                            url = ""
                            ready = False

                        if state != "deleted":
                            status_list.append(
                                {
                                    "is_datafile_tool": job.get("is_datafile_tool", False),
                                    "job_id": job["id"],
                                    "tool_id": job["tool_id"],
                                    "state": state,
                                    "url": url,
                                    "url_ready": ready,
                                }
                            )
                    except Exception:  # TODO: Might try to handle these better
                        continue
        except Exception as e:
            self._handle_galaxy_failure(e)

        return status_list

    def stop_job(self, tool_uid: str) -> None:
        with self.connection.connect() as connection:
            store = connection.create_data_store(name=settings.GALAXY_HISTORY_NAME)
            tool = Tool("")
            tool.assign_id(new_id=tool_uid, data_store=store)
            tool.cancel()
