"""Django views for the launcher app.

These views implement the URL schema
specified in urls.py file.
"""

import json
from importlib.resources import open_text
from typing import Any

from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import AbstractBaseUser
from django.core.exceptions import PermissionDenied
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseRedirect,
    JsonResponse,
    StreamingHttpResponse,
)
from django.shortcuts import redirect
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from requests import ConnectionError
from requests import request as proxy_request

from .auth import AuthManager
from .galaxy import GalaxyManager
from .notification import NotificationManager
from .status import StatusManager


def is_admin(user: AbstractBaseUser) -> bool:
    return user.get_username() in settings.NOVA_ADMINS


@require_GET
def logout_user(request: HttpRequest) -> HttpResponseRedirect:
    logout(request)

    return redirect("/")


@require_GET
def get_vuetify_config(request: HttpRequest) -> JsonResponse:
    with open_text("nova.trame.view.theme.assets", "vuetify_config.json") as vuetify_config:
        return JsonResponse(json.load(vuetify_config))


@require_GET
def ucams_redirect(request: HttpRequest) -> HttpResponseRedirect:
    auth_manager = AuthManager(request)
    user_info = auth_manager.redirect_handler(request, "ucams")

    email = user_info["email"]
    given_name = user_info["given_name"]

    auth_manager.login(request, email, given_name)

    response = redirect(settings.GALAXY_UCAMS_URL)
    response.set_cookie(
        settings.NOVA_LOGIN_COOKIE_NAME,
        f"{request.scheme}://{request.get_host()}/",
        30,
        httponly=True,
        secure=True,
        samesite="None",
    )
    return response


@require_GET
def xcams_redirect(request: HttpRequest) -> HttpResponseRedirect:
    auth_manager = AuthManager(request)
    user_info = auth_manager.redirect_handler(request, "xcams")

    email = user_info["email"]
    given_name = user_info["givenName"]

    auth_manager.login(request, email, given_name)

    response = redirect(settings.GALAXY_XCAMS_URL)
    response.set_cookie(
        settings.NOVA_LOGIN_COOKIE_NAME,
        f"{request.scheme}://{request.get_host()}/",
        30,
        httponly=True,
        secure=True,
        samesite="None",
    )
    return response


@require_GET
def get_alerts(request: HttpRequest) -> JsonResponse:
    status_manager = StatusManager()

    alert_data = {
        "alerts": status_manager.get_alerts(),
        "url": settings.MONITORING_URL if request.user.is_authenticated and is_admin(request.user) else "",
    }

    return JsonResponse(alert_data)


@require_GET
def get_targets(request: HttpRequest) -> JsonResponse:
    status_manager = StatusManager()

    return JsonResponse(status_manager.get_targets(), safe=False)


@ensure_csrf_cookie
@require_GET
def get_user(request: HttpRequest) -> JsonResponse:
    # This is the first request that the client makes to our API,
    # so we need to set the CSRF cookie here before any POST requests
    # are made.
    auth_manager = AuthManager(request)

    given_name = None
    admin = False
    if request.user.is_authenticated:
        given_name = request.user.first_name  # type: ignore
        admin = is_admin(request.user)

    return JsonResponse(
        {
            "given_name": given_name,
            "is_admin": admin,
            "is_logged_in": given_name is not None,
            "ucams": auth_manager.get_ucams_auth_url(),
            "xcams": auth_manager.get_xcams_auth_url(),
        }
    )


def _create_galaxy_error(exception: Exception, **kwargs: Any) -> JsonResponse:
    message = str(exception)
    if isinstance(exception, json.JSONDecodeError):
        message = f"Unable to fetch tool list, {settings.GALAXY_URL} may be restarting."
    if isinstance(exception, ConnectionError) or "502 Bad Gateway" in message:
        message = f"Unable to connect to Galaxy, {settings.GALAXY_URL} may be restarting."

    return JsonResponse({"error": message, **kwargs}, status=500)


def _create_galaxy_status_error(exception: Exception, auth_type: str, status_code: int) -> JsonResponse:
    return JsonResponse({"error": str(exception), "auth_type": auth_type.upper()}, status=status_code)


@login_required
@require_POST
def galaxy_launch(request: HttpRequest) -> HttpResponse:
    try:
        auth_manager = AuthManager(request)
        galaxy_manager = GalaxyManager(auth_manager)

        data = json.loads(request.body)
        job_id = galaxy_manager.launch_job(data.get("tool_id", None), data.get("inputs", {}))

        return JsonResponse({"id": job_id})
    except Exception as e:
        return _create_galaxy_error(e)


@login_required
@require_GET
def galaxy_user_status(request: HttpRequest) -> JsonResponse:
    session_type = ""
    try:
        auth_manager = AuthManager(request)
        auth_manager.delete_galaxy_api_key()  # Forces Galaxy to verify refresh token
        session_type = auth_manager.oauth_state.session_type
        GalaxyManager(auth_manager)

        return JsonResponse({"status": "ok"})
    except Exception as e:
        status_errors = ["Invalid access token", "Please login"]
        for status_error in status_errors:
            if status_error in str(e):
                return _create_galaxy_status_error(e, session_type, status_code=450)
        return _create_galaxy_error(e)


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
        return _create_galaxy_error(e, tools={})


@require_http_methods(["GET", "POST"])
def notification(request: HttpRequest) -> HttpResponse:
    notification_manager = NotificationManager()

    if request.method == "GET":
        return JsonResponse(notification_manager.get())

    if not request.user.is_authenticated or not is_admin(request.user):
        raise PermissionDenied

    try:
        data = json.loads(request.body.decode("utf-8"))
        notification_manager.set(data)
    except Exception:
        return HttpResponseBadRequest("message parameter is missing")

    return HttpResponse()


@require_GET
def client_proxy(request: HttpRequest) -> StreamingHttpResponse:
    """Proxy requests to the Vite dev server during development.

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
