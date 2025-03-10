"""Django views for the launcher app.

These views implement the URL schema
specified in urls.py file.
"""

import json
from importlib.resources import open_text

from django.contrib.auth.decorators import login_required
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseRedirect,
    JsonResponse,
    StreamingHttpResponse,
)
from django.shortcuts import redirect
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST
from requests import request as proxy_request

from .auth import AuthManager
from .galaxy import GalaxyManager


@require_GET
def get_vuetify_config(request: HttpRequest) -> JsonResponse:
    with open_text("trame_facade", "vuetify_config.json") as vuetify_config:
        return JsonResponse(json.load(vuetify_config))


@require_GET
def ucams_redirect(request: HttpRequest) -> HttpResponseRedirect:
    auth_manager = AuthManager(request)
    user_info = auth_manager.redirect_handler(request, "ucams")

    email = user_info["email"]
    given_name = user_info["given_name"]

    auth_manager.login(request, email, given_name)

    return redirect("/")


@require_GET
def xcams_redirect(request: HttpRequest) -> HttpResponseRedirect:
    auth_manager = AuthManager(request)
    user_info = auth_manager.redirect_handler(request, "xcams")

    email = user_info["email"]
    given_name = user_info["givenName"]

    auth_manager.login(request, email, given_name)

    return redirect("/")


@ensure_csrf_cookie
@require_GET
def get_user(request: HttpRequest) -> JsonResponse:
    # This is the first request that the client makes to our API,
    # so we need to set the CSRF cookie here before any POST requests
    # are made.
    auth_manager = AuthManager(request)

    given_name = None
    if request.user.is_authenticated:
        given_name = request.user.first_name  # type: ignore

    return JsonResponse(
        {
            "given_name": given_name,
            "is_logged_in": given_name is not None,
            "ucams": auth_manager.get_ucams_auth_url(),
            "xcams": auth_manager.get_xcams_auth_url(),
        }
    )


def _create_galaxy_error(exception: Exception) -> JsonResponse:
    return JsonResponse({"error": str(exception)}, status=500)


def _create_galaxy_status_error(exception: Exception, auth_type: str, status_code: int) -> JsonResponse:
    return JsonResponse({"error": str(exception), "auth_type": auth_type.upper()}, status=status_code)


@login_required
@require_POST
def galaxy_launch(request: HttpRequest) -> HttpResponse:
    try:
        auth_manager = AuthManager(request)
        galaxy_manager = GalaxyManager(auth_manager)

        data = json.loads(request.body)
        galaxy_manager.launch_job(data.get("tool_id", None))

        return HttpResponse()
    except Exception as e:
        return _create_galaxy_error(e)


@login_required
@require_GET
def galaxy_user_status(request: HttpRequest) -> JsonResponse:
    session_type = ""
    try:
        auth_manager = AuthManager(request)
        session_type = auth_manager.oauth_state.session_type
        GalaxyManager(auth_manager)

        return JsonResponse({"status": "ok"})
    except Exception as e:
        return _create_galaxy_status_error(e, session_type, status_code=450)


@login_required
@require_POST
def galaxy_monitor(request: HttpRequest) -> JsonResponse:
    try:
        auth_manager = AuthManager(request)
        galaxy_manager = GalaxyManager(auth_manager)
        data = json.loads(request.body)

        return JsonResponse({"jobs": galaxy_manager.monitor_jobs(data["tool_ids"])})
    except Exception as e:
        return _create_galaxy_error(e)


@login_required
@require_POST
def galaxy_stop(request: HttpRequest) -> HttpResponse:
    try:
        auth_manager = AuthManager(request)
        galaxy_manager = GalaxyManager(auth_manager)

        data = json.loads(request.body)
        galaxy_manager.stop_job(data.get("job_id", None))

        return HttpResponse()
    except Exception as e:
        return _create_galaxy_error(e)


@require_GET
def galaxy_tools(request: HttpRequest) -> JsonResponse:
    try:
        galaxy_manager = GalaxyManager()

        return JsonResponse({"tools": galaxy_manager.get_tools()})
    except Exception as e:
        return JsonResponse({"error": str(e), "tools": {}}, status=500)


@require_GET
def client_proxy(request: HttpRequest) -> StreamingHttpResponse:
    """Proxy requests to the VIte dev server during development.

    This method is only available in DEBUG mode.
    """
    proxy_response = proxy_request(
        "GET",
        f"http://localhost:5173{request.path}",
        headers=request.headers,
        stream=True,
    )

    response = StreamingHttpResponse(proxy_response.raw)
    response["Content-Type"] = proxy_response.headers["Content-Type"]

    return response
