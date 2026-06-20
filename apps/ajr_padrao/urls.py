from django.urls import path
from . import views

app_name = 'ajr_padrao'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
]
