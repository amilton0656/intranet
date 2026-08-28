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
    data_emissao = models.DateField(null=True, blank=True)
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


class ImportacaoAReceber(models.Model):
    """Registro de cada importação do CSV de contas a receber (Sienge)."""
    arquivo = models.CharField(max_length=255)
    importado_em = models.DateTimeField(auto_now_add=True)
    total_linhas = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-importado_em']
        verbose_name = 'Importação de A Receber'
        verbose_name_plural = 'Importações de A Receber'

    def __str__(self):
        return f'{self.arquivo} — {self.importado_em:%d/%m/%Y %H:%M}'


class ParcelaPendente(models.Model):
    """Uma linha de parcela em aberto do relatório de Contas a Receber do Sienge."""

    importacao = models.ForeignKey(
        ImportacaoAReceber, on_delete=models.CASCADE, related_name='parcelas'
    )

    codigo_empresa = models.CharField(max_length=20)
    nome_empresa = models.CharField(max_length=255)

    nome_cliente = models.CharField(max_length=255, blank=True, default='')
    numero_documento = models.CharField(max_length=40, blank=True, default='')
    numero_titulo = models.CharField(max_length=40, blank=True, default='')
    numero_parcela = models.CharField(max_length=20, blank=True, default='')
    tipo_condicao = models.CharField(max_length=10, blank=True, default='')
    numero_unidade = models.CharField(max_length=40, blank=True, default='')

    vencimento = models.DateField(null=True, blank=True)
    valor_original = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    valor_saldo_atual = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        ordering = ['vencimento']
        verbose_name = 'Parcela Pendente'
        verbose_name_plural = 'Parcelas Pendentes'
        indexes = [
            models.Index(fields=['numero_titulo']),
        ]

    def __str__(self):
        return f'{self.numero_titulo}/{self.numero_parcela} — R$ {self.valor_original}'


class Contrato(models.Model):
    """Um contrato (agrupamento de parcelas por NumeroDoTitulo), com o valor
    total vendido (já recebido + ainda pendente) e o mês em que foi vendido.

    Recalculado automaticamente a cada importação de Recebimento ou
    ParcelaPendente (ver `recalcular_contratos()`). `mes_venda_manual` é uma
    correção manual (editável no Admin) que tem prioridade sobre o mês
    calculado — usada para casos onde o dado de origem é ambíguo/errado.
    """

    codigo_empresa = models.CharField(max_length=20)
    nome_empresa = models.CharField(max_length=255)
    numero_titulo = models.CharField(max_length=40)

    nome_cliente = models.CharField(max_length=255, blank=True, default='')
    categoria = models.CharField(
        max_length=20, choices=Recebimento.CATEGORIA_CHOICES, default=Recebimento.OUTROS
    )
    codigo_centro_custo = models.CharField(max_length=20, blank=True, default='')
    nome_centro_custo = models.CharField(max_length=255, blank=True, default='')

    valor_recebido = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    valor_pendente = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    valor_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    mes_venda = models.DateField(null=True, blank=True)
    mes_venda_manual = models.DateField(
        null=True, blank=True,
        help_text='Sobrepõe o mês calculado automaticamente, quando preenchido.'
    )

    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-mes_venda']
        unique_together = [('codigo_empresa', 'numero_titulo')]
        verbose_name = 'Contrato'
        verbose_name_plural = 'Contratos'
        indexes = [
            models.Index(fields=['mes_venda']),
            models.Index(fields=['categoria']),
        ]

    def __str__(self):
        return f'{self.nome_empresa} — título {self.numero_titulo} — R$ {self.valor_total}'

    @property
    def mes_venda_efetivo(self):
        return self.mes_venda_manual or self.mes_venda
