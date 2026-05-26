from django.urls import path
from . import views

urlpatterns = [
    path('', views.intranet_home, name='intranet_home'),
    path('uploads/pdfs/', views.upload_pdfs, name='intranet_uploads'),
    path('financeiro/', views.financeiro_home, name='financeiro_home'),
    path('usuarios/', views.usuario_list, name='usuario_list'),
    path('usuarios/<int:pk>/grupos/', views.usuario_edit, name='usuario_edit'),
]
