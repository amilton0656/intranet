from django.db import models


def _fmt_brl(v):
    v = v or 0
    formatted = f'{v:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    return f'R$ {formatted}'


class ImportLog(models.Model):
    TIPOS = [
        ('clientes', 'Clientes'),
        ('vendas',   'Contratos de Venda'),
        ('locacoes', 'Contratos de Locação'),
    ]
    tipo            = models.CharField(max_length=20, choices=TIPOS, db_index=True)
    importado_em    = models.DateTimeField(auto_now_add=True)
    total_registros = models.IntegerField(default=0)
    nome_arquivo    = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-importado_em']

    def __str__(self):
        return f'{self.get_tipo_display()} — {self.importado_em:%d/%m/%Y %H:%M}'


class Cliente(models.Model):
    TIPO_PESSOA_CHOICES = [
        ('fisica',   'Física'),
        ('juridica', 'Jurídica'),
    ]

    codigo          = models.CharField('Código', max_length=20, unique=True)
    nome            = models.CharField('Nome', max_length=255)
    tipo_pessoa     = models.CharField('Tipo de Pessoa', max_length=10, choices=TIPO_PESSOA_CHOICES, blank=True)
    cpf_cnpj        = models.CharField('CPF/CNPJ', max_length=20, blank=True)
    data_nascimento = models.DateField('Data de Nascimento', null=True, blank=True)
    telefone        = models.CharField('Telefone', max_length=50, blank=True)
    email           = models.CharField('E-mail', max_length=255, blank=True)
    tipo_cliente    = models.CharField('Tipo de Cliente', max_length=100, blank=True, db_index=True)
    situacao        = models.CharField('Situação', max_length=20, blank=True)
    cidade          = models.CharField('Município', max_length=100, blank=True)
    uf              = models.CharField('UF', max_length=2, blank=True)
    atualizado_em   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'

    def __str__(self):
        return self.nome


class ContratoVenda(models.Model):
    cliente             = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='vendas')
    numero_contrato     = models.CharField('Contrato', max_length=50, unique=True)
    nome_empresa        = models.CharField('Empresa', max_length=255, blank=True)
    nome_empreendimento = models.CharField('Empreendimento', max_length=255, blank=True)
    unidade             = models.CharField('Unidade', max_length=50, blank=True)
    data_contrato       = models.DateField('Data do Contrato', null=True, blank=True)
    valor_total         = models.DecimalField('Valor Total', max_digits=14, decimal_places=2, default=0)
    tipo_venda          = models.CharField('Tipo de Venda', max_length=30, blank=True)
    situacao            = models.CharField('Situação', max_length=30, blank=True)
    corretor            = models.CharField('Corretor', max_length=255, blank=True)
    data_distrato       = models.DateField('Data do Distrato', null=True, blank=True)

    class Meta:
        ordering = ['-data_contrato']
        verbose_name = 'Contrato de Venda'
        verbose_name_plural = 'Contratos de Venda'

    def __str__(self):
        return f'{self.numero_contrato} — {self.cliente.nome}'

    @property
    def valor_total_fmt(self):
        return _fmt_brl(self.valor_total)


class ContratoLocacao(models.Model):
    cliente             = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='locacoes')
    numero_contrato     = models.CharField('Contrato', max_length=50, unique=True)
    nome_empresa        = models.CharField('Empresa', max_length=255, blank=True)
    nome_empreendimento = models.CharField('Empreendimento', max_length=255, blank=True)
    unidade             = models.CharField('Unidade', max_length=50, blank=True)
    data_contrato       = models.DateField('Data do Contrato', null=True, blank=True)
    valor_contrato      = models.DecimalField('Valor do Contrato', max_digits=14, decimal_places=2, default=0)
    valor_parcela       = models.DecimalField('Valor da Parcela', max_digits=14, decimal_places=2, default=0)
    tempo_locacao       = models.PositiveIntegerField('Tempo de Locação (meses)', null=True, blank=True)
    situacao            = models.CharField('Situação', max_length=30, blank=True)
    data_cancelamento   = models.DateField('Data do Cancelamento', null=True, blank=True)

    class Meta:
        ordering = ['-data_contrato']
        verbose_name = 'Contrato de Locação'
        verbose_name_plural = 'Contratos de Locação'

    def __str__(self):
        return f'{self.numero_contrato} — {self.cliente.nome}'

    @property
    def valor_contrato_fmt(self):
        return _fmt_brl(self.valor_contrato)
