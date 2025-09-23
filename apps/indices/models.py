# apps/indices/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Periodo(models.IntegerChoices):
    DIARIO = 1, 'Diário'
    MENSAL = 2, 'Mensal'

class Calculo(models.IntegerChoices):
    DIRETO = 1, 'Direto'
    ACUMULADO = 2, 'Acumulado'

class TipoRef(models.IntegerChoices):
    ANTERIOR = 1, 'Anterior'
    ATUAL = 2, 'Atual'

class Indice(models.Model):
    # use o id padrão do Django; evita id_indice manual
    descricao = models.CharField(
        max_length=40,
        verbose_name='Descrição',
        help_text='Nome curto do índice (ex.: IPCA, CDI, etc.)'
    )
    periodo = models.PositiveSmallIntegerField(
        choices=Periodo.choices,
        default=Periodo.MENSAL,
        verbose_name='Período'
    )
    calculo = models.PositiveSmallIntegerField(
        choices=Calculo.choices,
        default=Calculo.DIRETO,
        verbose_name='Cálculo'
    )
    tipo = models.PositiveSmallIntegerField(
        choices=TipoRef.choices,
        default=TipoRef.ATUAL,
        verbose_name='Tipo de referência'
    )
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        db_table = 'indices'          # mantém a mesma tabela
        ordering = ['descricao']
        verbose_name = 'Índice'
        verbose_name_plural = 'Índices'
        indexes = [
            models.Index(fields=['descricao']),
            models.Index(fields=['periodo', 'calculo', 'tipo']),
        ]

    def __str__(self):
        return f'{self.descricao} ({self.get_periodo_display()})'

class IndiceData(models.Model):
    # nome do campo pythonico; coluna no banco continua "id_indice"
    indice = models.ForeignKey(
        Indice,
        on_delete=models.CASCADE,
        related_name='datas',
        db_column='id_indice',
        verbose_name='Índice'
    )
    data = models.DateField(
        verbose_name='Data',
        help_text='Data de referência do índice (ex.: 2025-09-01)'
    )
    valor = models.DecimalField(
        max_digits=12,
        decimal_places=8,
        verbose_name='Valor',
        help_text='Valor do índice na data (p.ex.: 0.01023456 = 1,023456%)',
        validators=[MinValueValidator(-1_000_000), MaxValueValidator(1_000_000)]
    )
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        db_table = 'indices_datas'    # mantém a mesma tabela
        ordering = ['-data']
        verbose_name = 'Valor de Índice'
        verbose_name_plural = 'Valores de Índice'
        constraints = [
            models.UniqueConstraint(
                fields=['indice', 'data'],
                name='uniq_indice_data'
            )
        ]
        indexes = [
            models.Index(fields=['indice', 'data']),
            models.Index(fields=['data']),
        ]

    def __str__(self):
        return f'{self.indice.descricao} @ {self.data:%Y-%m-%d} = {self.valor}'
