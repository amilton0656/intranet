# from django.contrib import admin
from django.urls import path
# from django.contrib.auth import views as auth_views
from bliss.views import tab_bliss

urlpatterns = [
    path("", tab_bliss, name="tab_bliss"),
]
