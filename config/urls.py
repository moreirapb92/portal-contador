from api_alerta_backup import alerta_backup
from limpeza_segura import limpeza_segura
# -*- coding: utf-8 -*-

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path, include


urlpatterns = [
    path("api/alerta-backup/", alerta_backup, name="alerta_backup"),
    path("limpeza-segura/", limpeza_segura, name="limpeza_segura"),
    path("admin/", admin.site.urls),

    path(
        "login/",
        LoginView.as_view(template_name="registration/login.html"),
        name="login"
    ),

    path("logout/", LogoutView.as_view(), name="logout"),

    path("", include("portal.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)