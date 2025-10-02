from django.contrib import admin
from django.urls import path, include
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
    path('', include('apps.intranet.urls')),
    path('bliss/', include('apps.bliss.urls')),
    path('indices/', include('apps.indices.urls', namespace='indices')),
]
