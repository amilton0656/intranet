from django.db import models
from django.core.validators import RegexValidator


cnpj_validator = RegexValidator(
    regex=r'^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$',
    message='CNPJ deve estar no formato XX.XXX.XXX/XXXX-XX',
)


class Empresa(models.Model):
    razao_social = models.CharField('Razão Social', max_length=200)
    cnpj         = models.CharField('CNPJ', max_length=18, unique=True, validators=[cnpj_validator])
    ativo        = models.BooleanField('Ativo', default=True)

    class Meta:
        ordering = ['razao_social']
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'

    def __str__(self):
        return self.razao_social


class Empreendimento(models.Model):
    STATUS_CHOICES = [
        ('planejamento',   'Planejamento'),
        ('em_construcao',  'Em Construção'),
        ('entregue',       'Entregue'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name='empreendimentos', verbose_name='Empresa')
    nome    = models.CharField('Nome', max_length=200)
    status  = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='planejamento')

    class Meta:
        ordering = ['nome']
        verbose_name = 'Empreendimento'
        verbose_name_plural = 'Empreendimentos'

    def __str__(self):
        return self.nome


class Bloco(models.Model):
    empreendimento = models.ForeignKey(Empreendimento, on_delete=models.PROTECT, related_name='blocos', verbose_name='Empreendimento')
    nome           = models.CharField('Nome', max_length=100)

    class Meta:
        ordering = ['empreendimento', 'nome']
        verbose_name = 'Bloco'
        verbose_name_plural = 'Blocos'
        unique_together = [('empreendimento', 'nome')]

    def __str__(self):
        return f'{self.empreendimento} — {self.nome}'


class Unidade(models.Model):
    TIPO_CHOICES = [
        ('apartamento', 'Apartamento'),
        ('garagem',     'Garagem'),
        ('hobby_box',   'Hobby Box'),
        ('sala',        'Sala'),
        ('loja',        'Loja'),
    ]
    STATUS_CHOICES = [
        ('disponivel', 'Disponível'),
        ('reservado',  'Reservado'),
        ('vendido',    'Vendido'),
        ('permuta',    'Permuta'),
    ]

    bloco                    = models.ForeignKey(Bloco, on_delete=models.PROTECT, related_name='unidades', verbose_name='Bloco')
    unidade_principal        = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='vinculadas', verbose_name='Unidade Principal')
    ordem                    = models.IntegerField('Ordem', default=0)
    numero                   = models.CharField('Número', max_length=20)
    numeros_adicionais       = models.CharField('Números Adicionais', max_length=100, blank=True)
    tipo                     = models.CharField('Tipo', max_length=20, choices=TIPO_CHOICES, default='apartamento')
    tipologia                = models.CharField('Tipologia', max_length=100, blank=True)
    localizacao              = models.CharField('Localização', max_length=100, blank=True)
    area_privativa           = models.DecimalField('Área Privativa (m²)', max_digits=10, decimal_places=2, default=0)
    area_privativa_acessoria = models.DecimalField('Área Priv. Acessória (m²)', max_digits=10, decimal_places=2, default=0)
    area_comum               = models.DecimalField('Área Comum (m²)', max_digits=10, decimal_places=2, default=0)
    fracao_ideal             = models.DecimalField('Fração Ideal', max_digits=12, decimal_places=6, default=0)
    valor_tabela             = models.DecimalField('Valor Tabela (R$)', max_digits=14, decimal_places=2, default=0)
    status                   = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='disponivel')
    descricao1               = models.CharField('Descrição 1', max_length=255, blank=True)
    descricao2               = models.CharField('Descrição 2', max_length=255, blank=True)
    descricao3               = models.CharField('Descrição 3', max_length=255, blank=True)

    class Meta:
        ordering = ['bloco', 'ordem', 'numero']
        verbose_name = 'Unidade'
        verbose_name_plural = 'Unidades'
        unique_together = [('bloco', 'numero')]

    def __str__(self):
        return f'{self.bloco.empreendimento} — {self.bloco.nome} — {self.numero}'

    @property
    def numero_display(self):
        if self.numeros_adicionais:
            adicionais = ' · '.join(a.strip() for a in self.numeros_adicionais.split(',') if a.strip())
            return f'{self.numero} ({adicionais})'
        return self.numero

    @property
    def empreendimento(self):
        return self.bloco.empreendimento
