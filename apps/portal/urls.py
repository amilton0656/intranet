# from django.contrib import admin
from django.urls import path
# from django.contrib.auth import views as auth_views
from apps.portal.views import home

urlpatterns = [
    path("", home, name="home"),
]
