from django.db import models


class ImportacaoMaxFlora(models.Model):
    """Registro de cada importação do Excel."""
    arquivo = models.CharField(max_length=255)
    importado_em = models.DateTimeField(auto_now_add=True)
    total_unidades = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-importado_em']
        verbose_name = 'Importação Max & Flora'
        verbose_name_plural = 'Importações Max & Flora'

    def __str__(self):
        return f'{self.arquivo} — {self.importado_em:%d/%m/%Y %H:%M}'


class UnidadeMaxFlora(models.Model):
    SITUACAO_CHOICES = [
        ('LOCADO',      'Locado'),
        ('DISPONIVEL',  'Disponível'),
    ]

    importacao = models.ForeignKey(
        ImportacaoMaxFlora, on_delete=models.CASCADE, related_name='unidades'
    )
    euc           = models.CharField(max_length=20)           # "1 e 2", "3", "Estac."
    espaco        = models.PositiveSmallIntegerField(null=True, blank=True)
    locatario     = models.CharField(max_length=255, blank=True, default='')
    area_terreo   = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    area_mezanino = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    area_total    = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    valor_vendas  = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    situacao      = models.CharField(max_length=20, choices=SITUACAO_CHOICES,
                                     blank=True, default='DISPONIVEL')
    valor_aluguel = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    locado_ate    = models.DateField(null=True, blank=True)
    condominio    = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    iptu_tcrs     = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ordem         = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['ordem']
        verbose_name = 'Unidade Max & Flora'
        verbose_name_plural = 'Unidades Max & Flora'

    def __str__(self):
        return f'EUC {self.euc}'

    @property
    def locado(self):
        return self.situacao == 'LOCADO'
