"""URL configuration for launcher_app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/

Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.contrib import admin
from django.urls import path, re_path

from . import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("vuetify_config.json", views.get_vuetify_config),
    path("api/auth/user/", views.get_user),
    path("api/galaxy/user_status/", views.galaxy_user_status),
    path("api/galaxy/launch/", views.galaxy_launch),
    path("api/galaxy/monitor/", views.galaxy_monitor),
    path("api/galaxy/stop/", views.galaxy_stop),
    path("api/galaxy/tools/", views.galaxy_tools),
    path(settings.UCAMS_REDIRECT_PATH, views.ucams_redirect, name="ucams_redirect"),
    path(settings.XCAMS_REDIRECT_PATH, views.xcams_redirect, name="xcams_redirect"),
]

if settings.DEBUG:
    urlpatterns += [
        re_path("^.*/?$", views.client_proxy),
    ]
