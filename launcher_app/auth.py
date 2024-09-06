"""Defines a class for interacting with our OAuth providers.

The UCAMS/XCAMS OAuth providers must be configured via your .env file. See
.env.sample for the available configuration options.
"""

from typing import Any

from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.http import HttpRequest
from django.utils.crypto import get_random_string
from jwt import decode
from requests import get as requests_get
from requests.auth import HTTPBasicAuth
from requests_oauthlib import OAuth2Session

from launcher_app.models import OAuthSessionState


class AuthManager:
    """Class to manage Authentication for the Dashboard."""

    def __init__(self, request: HttpRequest):
        """Init."""
        if request.user.is_authenticated:
            self.oauth_state = OAuthSessionState.objects.get(user=request.user)
        else:
            try:
                self.oauth_state = OAuthSessionState.objects.get(
                    state_param=request.GET["state"]
                )
            except (KeyError, OAuthSessionState.DoesNotExist):
                self.oauth_state = OAuthSessionState.objects.create(
                    state_param=self.create_state_param()
                )

        self.ucams_session = OAuth2Session(
            settings.UCAMS_CLIENT_ID,
            auto_refresh_url=settings.UCAMS_TOKEN_URL,
            redirect_uri=settings.UCAMS_REDIRECT_URL,
            scope=settings.UCAMS_SCOPES.split(" "),
            token_updater=self.save_access_token,
        )
        self.xcams_session = OAuth2Session(
            settings.XCAMS_CLIENT_ID,
            auto_refresh_url=settings.XCAMS_TOKEN_URL,
            redirect_uri=settings.XCAMS_REDIRECT_URL,
            scope=settings.XCAMS_SCOPES.split(" "),
            token_updater=self.save_access_token,
        )

    def create_state_param(self) -> str:
        return get_random_string(length=128)

    def delete_galaxy_api_key(self) -> None:
        self.oauth_state.galaxy_api_key = ""
        self.oauth_state.save()

    def login(self, request: HttpRequest, email: str, given_name: str) -> None:
        try:
            user = get_user_model().objects.get(username=email)
        except get_user_model().DoesNotExist:
            user = get_user_model().objects.create_user(
                username=email, email=email, first_name=given_name
            )

        login(request, user)

        # Removing old session states both reduces the size of the database over
        # time and allows us to make OAuthSessionState.user a OneToOneField.
        OAuthSessionState.objects.filter(user=user).delete()

        self.oauth_state.user = user
        self.oauth_state.save()

    def redirect_handler(
        self, request: HttpRequest, session_type: str
    ) -> dict[str, Any]:
        self.oauth_state.session_type = session_type
        self.oauth_state.save()

        match session_type:
            case "ucams":
                tokens = self.ucams_session.fetch_token(
                    settings.UCAMS_TOKEN_URL,
                    authorization_response=request.build_absolute_uri(),
                    client_secret=settings.UCAMS_CLIENT_SECRET,
                )
            case "xcams":
                tokens = self.xcams_session.fetch_token(
                    settings.XCAMS_TOKEN_URL,
                    authorization_response=request.build_absolute_uri(),
                    client_secret=settings.XCAMS_CLIENT_SECRET,
                )

        self.save_access_token(tokens["access_token"])
        self.save_refresh_token(tokens["refresh_token"])

        return decode(tokens["id_token"], options={"verify_signature": False})

    def get_galaxy_api_key(self) -> str:
        if self.oauth_state.galaxy_api_key == "":
            access_token = self.get_access_token()
            response = requests_get(
                f"{settings.GALAXY_URL}{settings.GALAXY_API_KEY_ENDPOINT}",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            data = response.json()
            if "err_msg" in data:
                raise Exception(data["err_msg"])

            self.oauth_state.galaxy_api_key = response.json()["api_key"]
            self.oauth_state.save()

        return self.oauth_state.galaxy_api_key

    def get_access_token(self) -> str:
        match self.oauth_state.session_type:
            case "ucams":
                tokens = self.ucams_session.refresh_token(
                    settings.UCAMS_TOKEN_URL,
                    auth=HTTPBasicAuth(
                        settings.UCAMS_CLIENT_ID, settings.UCAMS_CLIENT_SECRET
                    ),
                    refresh_token=self.get_refresh_token(),
                )
            case "xcams":
                tokens = self.xcams_session.refresh_token(
                    settings.XCAMS_TOKEN_URL,
                    auth=HTTPBasicAuth(
                        settings.XCAMS_CLIENT_ID, settings.XCAMS_CLIENT_SECRET
                    ),
                    refresh_token=self.get_refresh_token(),
                )

        self.save_access_token(tokens["access_token"])
        self.save_refresh_token(tokens["refresh_token"])

        return self.oauth_state.access_token

    def get_refresh_token(self) -> str:
        return (
            Fernet(settings.REFRESH_TOKEN_KEY)
            .decrypt(self.oauth_state.refresh_token.encode())
            .decode()
        )

    def get_ucams_auth_url(self) -> str:
        return self.ucams_session.authorization_url(settings.UCAMS_AUTH_URL)[0]

    def get_xcams_auth_url(self) -> str:
        return self.xcams_session.authorization_url(settings.XCAMS_AUTH_URL)[0]

    def save_access_token(self, token: str) -> None:
        self.oauth_state.access_token = token
        self.oauth_state.save()

    def save_refresh_token(self, token: str) -> None:
        self.oauth_state.refresh_token = (
            Fernet(settings.REFRESH_TOKEN_KEY).encrypt(token.encode()).decode()
        )
        self.oauth_state.save()
