from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.intranet.urls')),
    path('indices/', include('apps.indices.urls', namespace='indices')),
]
