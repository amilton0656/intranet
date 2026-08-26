from django.db import models


class ImportacaoFaturamento(models.Model):
    """Registro de cada importação do CSV de faturamento (Sienge)."""
    arquivo = models.CharField(max_length=255)
    importado_em = models.DateTimeField(auto_now_add=True)
    total_linhas = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-importado_em']
        verbose_name = 'Importação de Faturamento'
        verbose_name_plural = 'Importações de Faturamento'

    def __str__(self):
        return f'{self.arquivo} — {self.importado_em:%d/%m/%Y %H:%M}'


class Recebimento(models.Model):
    """Uma linha de baixa (recebimento) do relatório do Sienge.

    Categoria é determinada pelo prefixo da conta no Plano de Contas
    (ver plano financeiro.pdf): 1.01.* = Incorporação, 1.03.* = Locação.
    """
    INCORPORACAO = 'INCORPORACAO'
    LOCACAO = 'LOCACAO'
    OUTROS = 'OUTROS'
    CATEGORIA_CHOICES = [
        (INCORPORACAO, 'Incorporação'),
        (LOCACAO, 'Locações'),
        (OUTROS, 'Outros'),
    ]

    importacao = models.ForeignKey(
        ImportacaoFaturamento, on_delete=models.CASCADE, related_name='recebimentos'
    )

    codigo_empresa = models.CharField(max_length=20)
    nome_empresa = models.CharField(max_length=255)

    codigo_centro_custo = models.CharField(max_length=20, blank=True, default='')
    nome_centro_custo = models.CharField(max_length=255, blank=True, default='')

    codigo_cliente = models.CharField(max_length=20, blank=True, default='')
    nome_cliente = models.CharField(max_length=255, blank=True, default='')

    numero_titulo = models.CharField(max_length=40, blank=True, default='')
    numero_parcela = models.CharField(max_length=20, blank=True, default='')
    numero_unidade = models.CharField(max_length=40, blank=True, default='')

    codigo_plano_financeiro = models.CharField(max_length=20, blank=True, default='')
    nome_plano_financeiro = models.CharField(max_length=255, blank=True, default='')
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default=OUTROS)

    data_baixa = models.DateField()
    valor_baixa = models.DecimalField(max_digits=14, decimal_places=2)
    valor_liquido = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        ordering = ['-data_baixa']
        verbose_name = 'Recebimento'
        verbose_name_plural = 'Recebimentos'
        indexes = [
            models.Index(fields=['data_baixa']),
            models.Index(fields=['categoria']),
        ]

    def __str__(self):
        return f'{self.nome_cliente} — {self.data_baixa:%d/%m/%Y} — R$ {self.valor_liquido}'
