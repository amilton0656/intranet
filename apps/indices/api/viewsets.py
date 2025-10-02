from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from apps.indices.models import Indice, IndiceData
from .serializers import ApiIndicesSerializer, ApiIndiceDatasSerializer
from rest_framework.decorators import action
from django.db import connection
from rest_framework.permissions import DjangoModelPermissions


class ApiIndicesViewSet(ModelViewSet):
    permission_classes = (DjangoModelPermissions,)
    queryset = Indice.objects.all()
    serializer_class = ApiIndicesSerializer

class ApiIndiceDatasViewSet(ModelViewSet):
    queryset = IndiceData.objects.all()
    serializer_class = ApiIndiceDatasSerializer


    