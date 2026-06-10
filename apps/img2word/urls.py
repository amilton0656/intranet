from django.urls import path
from . import views

app_name = 'img2word'

urlpatterns = [
    path('', views.index, name='index'),
]
