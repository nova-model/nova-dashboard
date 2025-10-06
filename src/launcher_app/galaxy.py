"""Defines a class for interacting with a specified Galaxy server.

The server to connect to can be controlled via the GALAXY_URL setting.
The endpoint on the server through which to get a user's API key can be
controlled via the GALAXY_API_KEY_ENDPOINT setting.
The history name to use for all jobs can be controlled via the
GALAXY_HISTORY_NAME setting.
"""

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
        tool_json = {}

        # Retrieve the tool name and help text from the Galaxy server.
        galaxy_tools = requests_get(f"{settings.GALAXY_URL}/api/tools?tool_help=true").json()
        for galaxy_category in galaxy_tools:
            category_id = galaxy_category.get("id", "generic-tools")
            category_name = galaxy_category.get("name", "General-Purpose Tools")
            category_description = galaxy_category.get("description", "")

            tool_json[category_id] = {
                "name": category_name,
                "description": category_description,
                "tools": [],
                "prototype_tools": [],
            }

            for tool in galaxy_category.get("elems", []):
                tool_id = tool["id"]
                if "nova" not in tool_id:
                    continue

                tool_description = self._parse_tool_help(tool.get("help", ""))
                tool_name = tool.get("name", "Unnamed Tool")
                tool_version = tool.get("version", "unversioned")

                if "prototype" in tool_id:
                    tool_json[category_id]["prototype_tools"].append(
                        {"id": tool_id, "description": tool_description, "name": tool_name, "version": tool_version}
                    )
                else:
                    tool_json[category_id]["tools"].append(
                        {"id": tool_id, "description": tool_description, "name": tool_name, "version": tool_version}
                    )

        for category_id in list(tool_json.keys()):
            if not tool_json[category_id]["tools"] and not tool_json[category_id]["prototype_tools"]:
                del tool_json[category_id]

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
                            data = {
                                "is_datafile_tool": job.get("is_datafile_tool", False),
                                "job_id": job["id"],
                                "tool_id": job["tool_id"],
                                "state": state,
                                "url": url,
                                "url_ready": ready,
                            }
                            if data["is_datafile_tool"]:
                                parameters = connection.galaxy_instance.jobs.show_job(data["job_id"]).get("params", {})
                                # Clean up some Galaxy nonsense
                                for key in ["chromInfo", "dbkey", "__input_ext"]:
                                    parameters.pop(key, None)
                                data["parameters"] = parameters

                            status_list.append(data)
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
