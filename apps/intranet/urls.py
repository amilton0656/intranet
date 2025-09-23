from django.urls import path
from . import views

urlpatterns = [
    path('', views.intranet_home, name='intranet_home')
]
