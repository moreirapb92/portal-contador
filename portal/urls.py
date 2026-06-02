# -*- coding: utf-8 -*-

from django.urls import path

from . import views
from . import api


app_name = "portal"

urlpatterns = [
    path("", views.home, name="home"),
    path("empresa/<int:empresa_id>/", views.dashboard_empresa, name="dashboard_empresa"),
    path("empresa/<int:empresa_id>/upload-xml/", views.upload_xml_empresa, name="upload_xml_empresa"),

    path("api/upload-xml/", api.upload_xml_api, name="upload_xml_api"),
]