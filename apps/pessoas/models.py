from django.db import models


class Pessoa(models.Model):
    TIPO_CHOICES = [
        ('fisica',   'Pessoa Física'),
        ('juridica', 'Pessoa Jurídica'),
    ]
    ESTADO_CHOICES = [
        ('AC','AC'),('AL','AL'),('AP','AP'),('AM','AM'),('BA','BA'),('CE','CE'),
        ('DF','DF'),('ES','ES'),('GO','GO'),('MA','MA'),('MT','MT'),('MS','MS'),
        ('MG','MG'),('PA','PA'),('PB','PB'),('PR','PR'),('PE','PE'),('PI','PI'),
        ('RJ','RJ'),('RN','RN'),('RS','RS'),('RO','RO'),('RR','RR'),('SC','SC'),
        ('SP','SP'),('SE','SE'),('TO','TO'),
    ]
    ESTADO_CIVIL_CHOICES = [
        ('solteiro',      'Solteiro(a)'),
        ('casado',        'Casado(a)'),
        ('divorciado',    'Divorciado(a)'),
        ('viuvo',         'Viúvo(a)'),
        ('uniao_estavel', 'União Estável'),
        ('separado',      'Separado(a) Judicialmente'),
    ]
    REGIME_BENS_CHOICES = [
        ('comunhao_parcial',   'Comunhão Parcial de Bens'),
        ('comunhao_universal', 'Comunhão Universal de Bens'),
        ('separacao_total',    'Separação Total de Bens'),
        ('participacao_final', 'Participação Final nos Aquestos'),
    ]
    TIPO_CONTA_CHOICES = [
        ('corrente', 'Corrente'),
        ('poupanca', 'Poupança'),
    ]

    tipo        = models.CharField('Tipo', max_length=10, choices=TIPO_CHOICES, default='fisica')
    nome        = models.CharField('Nome / Razão Social', max_length=200)
    cpf_cnpj    = models.CharField('CPF / CNPJ', max_length=20, blank=True)
    rg_ie       = models.CharField('RG / Insc. Estadual', max_length=30, blank=True)
    rg_orgao_emissor = models.CharField('Órgão Emissor', max_length=20, blank=True)

    # Pessoa Física
    nacionalidade = models.CharField('Nacionalidade', max_length=60, blank=True, default='brasileiro(a)')
    profissao     = models.CharField('Profissão', max_length=100, blank=True)
    estado_civil  = models.CharField('Estado Civil', max_length=20, choices=ESTADO_CIVIL_CHOICES, blank=True)
    regime_bens   = models.CharField('Regime de Bens', max_length=30, choices=REGIME_BENS_CHOICES, blank=True)

    # Pessoa Jurídica
    tipo_societario = models.CharField('Tipo Societário', max_length=60, blank=True,
                                       help_text='Ex: Ltda, S/A, EIRELI, MEI')
    representante   = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL,
                                        related_name='representa_pj', verbose_name='Representante Legal')

    email       = models.EmailField('E-mail', blank=True)
    telefone    = models.CharField('Telefone', max_length=20, blank=True)
    celular     = models.CharField('Celular', max_length=20, blank=True)

    cep         = models.CharField('CEP', max_length=9, blank=True)
    logradouro  = models.CharField('Logradouro', max_length=200, blank=True)
    numero      = models.CharField('Número', max_length=20, blank=True)
    complemento = models.CharField('Complemento', max_length=100, blank=True)
    bairro      = models.CharField('Bairro', max_length=100, blank=True)
    cidade      = models.CharField('Cidade', max_length=100, blank=True)
    estado      = models.CharField('Estado', max_length=2, choices=ESTADO_CHOICES, blank=True)

    is_cliente     = models.BooleanField('Cliente',     default=False)
    is_corretor    = models.BooleanField('Corretor',    default=False)
    is_imobiliaria = models.BooleanField('Imobiliária', default=False)
    is_fornecedor  = models.BooleanField('Fornecedor',  default=False)
    is_outro       = models.BooleanField('Outro',       default=False)

    # Dados bancários
    banco_nome       = models.CharField('Banco', max_length=100, blank=True)
    banco_agencia    = models.CharField('Agência', max_length=20, blank=True)
    banco_conta      = models.CharField('Conta', max_length=30, blank=True)
    banco_tipo_conta = models.CharField('Tipo de Conta', max_length=15, choices=TIPO_CONTA_CHOICES, blank=True)

    observacoes = models.TextField('Observações', blank=True)
    ativo       = models.BooleanField('Ativo', default=True)

    criado_em   = models.DateTimeField(auto_now_add=True)
    alterado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'Pessoa'
        verbose_name_plural = 'Pessoas'

    def __str__(self):
        return self.nome

    @property
    def papeis_display(self):
        papeis = []
        if self.is_cliente:     papeis.append('Cliente')
        if self.is_corretor:    papeis.append('Corretor')
        if self.is_imobiliaria: papeis.append('Imobiliária')
        if self.is_fornecedor:  papeis.append('Fornecedor')
        if self.is_outro:       papeis.append('Outro')
        return papeis
