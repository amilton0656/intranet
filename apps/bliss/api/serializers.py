from  rest_framework.serializers import ModelSerializer
from apps.bliss.models import Bliss


class ApiBlissSerializer(ModelSerializer):
    class Meta: 
        model = Bliss
        fields = ('id', 'bloco', 'unidade', 'perc_permuta', 'area_privativa',
                  'area_total', 'garagem', 'deposito', 'tipologia', 'situacao', 
                  'valor_tabela', 'valor_venda', 'data_venda', 'cliente', 'email'
                  )
