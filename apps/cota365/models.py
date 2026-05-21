from django.db import models


class ImportLog(models.Model):
    TIPOS = [
        ('tabela',   'Tabela de Preços'),
        ('unidades', 'Unidades'),
        ('vendas',   'Vendas'),
        ('fluxo',    'Fluxo de Caixa'),
        ('vinculo',  'Vínculos'),
        ('permutas', 'Permutas'),
    ]
    tipo             = models.CharField(max_length=20, choices=TIPOS)
    importado_em     = models.DateTimeField(auto_now_add=True)
    total_registros  = models.IntegerField(default=0)
    nome_arquivo     = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-importado_em']

    def __str__(self):
        return f'{self.get_tipo_display()} — {self.importado_em:%d/%m/%Y %H:%M}'


class Tabela(models.Model):
    unidade        = models.CharField(max_length=50, unique=True)
    tipologia      = models.CharField(max_length=100, blank=True)
    situacao       = models.CharField(max_length=50, blank=True)
    area_privativa = models.FloatField(default=0)
    valor_total    = models.FloatField(default=0)

    def __str__(self):
        return self.unidade


class Permuta(models.Model):
    unidade = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.unidade


class Vinculo(models.Model):
    unidade  = models.CharField(max_length=50, unique=True)
    garagens = models.CharField(max_length=100, blank=True)
    hb       = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.unidade


class Venda(models.Model):
    numero      = models.CharField(max_length=20, unique=True)
    situacao    = models.CharField(max_length=50, blank=True)
    unidade     = models.CharField(max_length=50, blank=True)
    cliente     = models.CharField(max_length=255, blank=True)
    imobiliaria = models.CharField(max_length=255, blank=True)
    m2          = models.CharField(max_length=20, blank=True)
    espacos     = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f'#{self.numero} — {self.cliente}'


class Unidade(models.Model):
    unidade             = models.CharField(max_length=50, unique=True)
    tipo                = models.CharField(max_length=100, blank=True)
    complemento_tipo    = models.CharField(max_length=100, blank=True)
    area_privativa      = models.FloatField(default=0)
    area_priv_acessoria = models.FloatField(default=0)
    area_comum          = models.FloatField(default=0)
    fracao_ideal        = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return self.unidade


class FluxoContrato(models.Model):
    id_contrato     = models.CharField(max_length=20, blank=True)
    cliente         = models.CharField(max_length=255, blank=True)
    unidade         = models.CharField(max_length=50, blank=True)
    empreendimento  = models.CharField(max_length=255, blank=True)
    vgv             = models.FloatField(default=0)
    pv              = models.FloatField(default=0)
    primeira_parcela = models.DateField()
    ultima_parcela  = models.DateField(null=True, blank=True)
    imobiliaria     = models.CharField(max_length=255, blank=True)
    corretor        = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f'{self.id_contrato} — {self.cliente}'


class FluxoParcela(models.Model):
    contrato = models.ForeignKey(FluxoContrato, on_delete=models.CASCADE, related_name='parcelas')
    mes_idx  = models.SmallIntegerField()
    valor    = models.FloatField(default=0)

    class Meta:
        ordering = ['mes_idx']


class Comissao(models.Model):
    numero               = models.CharField(max_length=20, unique=True)
    situacao             = models.CharField(max_length=100, blank=True)
    reserva              = models.CharField(max_length=20, blank=True)
    corretor             = models.CharField(max_length=255, blank=True)
    data_venda           = models.DateField(null=True, blank=True)
    imobiliaria          = models.CharField(max_length=255, blank=True)
    unidade              = models.CharField(max_length=50, blank=True)
    cliente              = models.CharField(max_length=255, blank=True)
    tipo_unidade         = models.CharField(max_length=100, blank=True)
    valor_contrato       = models.FloatField(default=0)
    pct_comissao         = models.FloatField(default=0)
    valor_comissao       = models.FloatField(default=0)
    pct_premio           = models.FloatField(default=0)
    valor_premio         = models.FloatField(default=0)
    tipo_comissao        = models.CharField(max_length=100, blank=True)
    valor_comissao_pagar = models.FloatField(default=0)
    data_prevista        = models.DateField(null=True, blank=True)
    data_pagamento       = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['numero']

    def __str__(self):
        return f'#{self.numero} — {self.cliente}'
