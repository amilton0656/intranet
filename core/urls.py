from django.conf import settings
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve
from rest_framework import routers

from apps.indices.api.viewsets import ApiIndicesViewSet, ApiIndiceDatasViewSet
from apps.bliss.api.viewsets import ApiBlissViewSet

router = routers.DefaultRouter()
router.register(r'indices', ApiIndicesViewSet)
router.register(r'indicedatas', ApiIndiceDatasViewSet)
router.register(r'bliss',ApiBlissViewSet)
# router.register(r'pontoturistico', PontoTuristicoViewSet, basename='PontoTuristico')

urlpatterns = [
    path('api/', include(router.urls)),
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('chat/', include(('apps.chat.urls', 'chat'), namespace='chat')),
    path('', include('apps.intranet.urls')),
    path('bliss/', include('apps.bliss.urls')),
    path('indices/', include('apps.indices.urls', namespace='indices')),
    path('cota365/', include('apps.cota365.urls', namespace='cota365')),
    path('incorporadora/', include('apps.incorporadora.urls', namespace='incorporadora')),
    path('pessoas/', include('apps.pessoas.urls', namespace='pessoas')),
    path('propostas/', include('apps.propostas.urls', namespace='propostas')),
    path('contratos/', include('apps.contratos.urls', namespace='contratos')),
    path('img2word/', include('apps.img2word.urls', namespace='img2word')),
    path('maxflora/', include('apps.maxflora.urls', namespace='maxflora')),
    path('ajr-padrao/', include('apps.ajr_padrao.urls', namespace='ajr_padrao')),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
