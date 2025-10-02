from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from apps.bliss.models import Bliss
from .serializers import ApiBlissSerializer
from rest_framework.decorators import action
from django.db import connection


class ApiBlissViewSet(ModelViewSet):
    queryset = Bliss.objects.all()
    serializer_class = ApiBlissSerializer

    