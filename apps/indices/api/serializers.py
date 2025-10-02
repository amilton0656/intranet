from  rest_framework.serializers import ModelSerializer
from apps.indices.models import Indice, IndiceData


class ApiIndicesSerializer(ModelSerializer):
    class Meta: 
        model = Indice
        fields = ('id', 'descricao', 'periodo', 'calculo', 'tipo')

class ApiIndiceDatasSerializer(ModelSerializer):
    class Meta: 
        model = IndiceData
        fields = ('id', 'indice', 'data', 'valor')