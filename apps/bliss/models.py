from django.db import models


class Bliss(models.Model):
    bloco = models.CharField(max_length=20)
    unidade = models.CharField(max_length=20)
    perc_permuta = models.DecimalField(max_digits=10, decimal_places=6, default=1)
    area_privativa = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    area_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    garagem = models.CharField(max_length=30, blank=True, null=True)
    deposito = models.CharField(max_length=20, blank=True, null=True)
    tipologia = models.CharField(max_length=20, blank=True, null=True)
    situacao = models.CharField(max_length=30)
    valor_tabela = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    valor_venda = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    data_venda = models.DateField(blank=True, null=True)
    cliente = models.CharField(max_length=100, blank=True, null=True)
    email = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        db_table = 'unidades_bliss'
        ordering = ['bloco', 'unidade']

    def __str__(self):
        return f"{self.bloco}-{self.unidade}"
