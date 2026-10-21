from django.urls import path

from alerts.api import api

urlpatterns = [path("", api.urls)]
