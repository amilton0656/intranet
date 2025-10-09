from django.urls import path

from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.chat_view, name='chat'),
    path('bliss-memorial/', views.bliss_memorial_view, name='bliss_memorial'),
]
