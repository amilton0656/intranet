from django.conf import settings
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
        ('bloqueado',  'Bloqueado'),
        ('qa',         'QA'),
    ]

    bloco                    = models.ForeignKey(Bloco, on_delete=models.PROTECT, related_name='unidades', verbose_name='Bloco')
    unidade_principal        = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='vinculadas', verbose_name='Unidade Principal')
    ordem                    = models.IntegerField('Ordem', default=0)
    numero                   = models.CharField('Número', max_length=20)
    numeros_adicionais       = models.CharField('Números Adicionais', max_length=100, blank=True)
    tipo                     = models.CharField('Tipo', max_length=20, choices=TIPO_CHOICES, default='apartamento')
    tipologia                = models.CharField('Tipologia', max_length=100, blank=True)
    localizacao              = models.CharField('Localização', max_length=100, blank=True)
    area_privativa           = models.DecimalField('Área Privativa (m²)', max_digits=10, decimal_places=4, default=0)
    area_privativa_acessoria = models.DecimalField('Área Priv. Acessória (m²)', max_digits=10, decimal_places=4, default=0)
    area_comum               = models.DecimalField('Área Comum (m²)', max_digits=10, decimal_places=4, default=0)
    fracao_ideal             = models.DecimalField('Fração Ideal', max_digits=12, decimal_places=6, default=0)
    valor_tabela             = models.DecimalField('Valor Tabela (R$)', max_digits=14, decimal_places=2, default=0)
    perc_permuta             = models.DecimalField('% Permuta', max_digits=8, decimal_places=6, default=0,
                                                   help_text='Fração do valor/área destinada à permuta (ex: 0.12826). 0 = sem permuta parcial.')
    status                   = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='disponivel')
    pagina                   = models.PositiveIntegerField('Página', default=1)
    cliente_nome             = models.CharField('Cliente', max_length=200, blank=True)
    cliente_email            = models.CharField('E-mail do Cliente', max_length=200, blank=True)
    descricao1               = models.CharField('Descrição 1', max_length=255, blank=True)
    descricao2               = models.CharField('Descrição 2', max_length=255, blank=True)
    descricao3               = models.CharField('Descrição 3', max_length=255, blank=True)

    class Meta:
        ordering = ['bloco', 'ordem', 'numero']
        verbose_name = 'Unidade'
        verbose_name_plural = 'Unidades'
        unique_together = [('bloco', 'numero')]

    @property
    def area_total(self):
        return self.area_privativa + self.area_privativa_acessoria + self.area_comum

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


class TabelaVendas(models.Model):
    MODALIDADE_CHOICES = [
        ('bancaria', 'Bancária'),
        ('direta',   'Direta'),
        ('outra',    'Outra'),
    ]

    empreendimento  = models.ForeignKey(Empreendimento, on_delete=models.PROTECT, related_name='tabelas', verbose_name='Empreendimento')
    nome            = models.CharField('Nome', max_length=200)
    modalidade      = models.CharField('Modalidade', max_length=20, choices=MODALIDADE_CHOICES, default='bancaria')
    cub_referencia  = models.DecimalField('CUB de Referência', max_digits=10, decimal_places=2, default=0)
    data_referencia = models.DateField('Data de Referência')
    data_inicio     = models.DateField('Início de Vigência', null=True, blank=True)
    data_fim        = models.DateField('Fim de Vigência', null=True, blank=True)
    ativa           = models.BooleanField('Ativa', default=True)
    criado_em       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_referencia', 'nome']
        verbose_name = 'Tabela de Vendas'
        verbose_name_plural = 'Tabelas de Vendas'

    def __str__(self):
        return f'{self.empreendimento} — {self.nome}'


class SeriePagamento(models.Model):
    TIPO_CHOICES = [
        ('ato',          'Ato'),
        ('parcela',      'Parcela'),
        ('reforco',      'Reforço'),
        ('chaves',       'Chaves'),
        ('financiamento','Financiamento'),
        ('outro',        'Outro'),
    ]
    PERIODICIDADE_CHOICES = [
        ('unico',      'Único'),
        ('mensal',     'Mensal'),
        ('bimestral',  'Bimestral'),
        ('trimestral', 'Trimestral'),
        ('semestral',  'Semestral'),
        ('anual',      'Anual'),
    ]
    INDICE_CHOICES = [
        ('cub',  'CUB'),
        ('igpm', 'IGPM'),
        ('fixo', 'Fixo'),
    ]

    tabela               = models.ForeignKey(TabelaVendas, on_delete=models.CASCADE, related_name='series', verbose_name='Tabela')
    tipo                 = models.CharField('Tipo', max_length=20, choices=TIPO_CHOICES, default='outro')
    periodicidade        = models.CharField('Periodicidade', max_length=20, choices=PERIODICIDADE_CHOICES, default='unico')
    primeiro_vencimento  = models.DateField('Primeiro Vencimento', null=True, blank=True)
    quantidade           = models.PositiveIntegerField('Quantidade', default=1)
    percentual           = models.DecimalField('Percentual do Valor (%)', max_digits=6, decimal_places=3,
                                               null=True, blank=True,
                                               help_text='Percentual do valor de venda da unidade para esta série. Ex: 20 = 20%')
    indice               = models.CharField('Índice de Reajuste', max_length=10, choices=INDICE_CHOICES, default='cub')
    ordem                = models.PositiveIntegerField('Ordem', default=0)

    class Meta:
        ordering = ['tabela', 'ordem']
        verbose_name = 'Série de Pagamento'
        verbose_name_plural = 'Séries de Pagamento'

    def __str__(self):
        return f'{self.quantidade}x {self.get_tipo_display()}'

    @property
    def label(self):
        """Cabeçalho da coluna na tabela de vendas."""
        if self.quantidade > 1:
            return f'{self.quantidade}x {self.get_tipo_display()}'
        return self.get_tipo_display()


class ItemTabelaVendas(models.Model):
    STATUS_CHOICES = [
        ('disponivel',    'Disponível'),
        ('vendido',       'Vendido'),
        ('permuta',       'Permuta'),
        ('contrato',      'Contrato'),
        ('em_negociacao', 'Em Negociação'),
        ('reserva',       'Reserva'),
        ('proprio',       'Próprio'),
    ]

    tabela      = models.ForeignKey(TabelaVendas, on_delete=models.CASCADE, related_name='itens', verbose_name='Tabela')
    unidade     = models.ForeignKey(Unidade, on_delete=models.PROTECT, related_name='itens_tabela', verbose_name='Unidade')
    status      = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='disponivel')
    valor_venda = models.DecimalField('Valor de Venda (R$)', max_digits=14, decimal_places=2, default=0)

    class Meta:
        ordering = ['unidade__bloco__nome', 'unidade__pagina', 'unidade__ordem', 'unidade__numero']
        unique_together = [('tabela', 'unidade')]
        verbose_name = 'Item de Tabela de Vendas'
        verbose_name_plural = 'Itens de Tabela de Vendas'

    def __str__(self):
        return f'{self.tabela} — {self.unidade.numero}'


class ValorSerie(models.Model):
    item          = models.ForeignKey(ItemTabelaVendas, on_delete=models.CASCADE, related_name='valores', verbose_name='Item')
    serie         = models.ForeignKey(SeriePagamento, on_delete=models.CASCADE, related_name='valores', verbose_name='Série')
    valor_parcela = models.DecimalField('Valor por Parcela (R$)', max_digits=14, decimal_places=2, default=0)

    class Meta:
        unique_together = [('item', 'serie')]
        verbose_name = 'Valor de Série'
        verbose_name_plural = 'Valores de Série'

    def __str__(self):
        return f'{self.serie} — R$ {self.valor_parcela}'


class ImportLog(models.Model):
    TIPO_CHOICES = [
        ('tabela_cv',          'Tabela CV (situação + valor)'),
        ('unidades',           'Unidades (dados completos)'),
        ('vinculos',           'Vínculos (garagens/HBs)'),
        ('atualizacao_mensal', 'Atualização Mensal'),
        ('vendas',             'Vendas (cliente/imobiliária)'),
    ]

    empreendimento  = models.ForeignKey(Empreendimento, on_delete=models.CASCADE,
                                        related_name='import_logs', verbose_name='Empreendimento')
    tipo            = models.CharField('Tipo', max_length=30, choices=TIPO_CHOICES, db_index=True)
    nome_arquivo    = models.CharField('Arquivo', max_length=255)
    total_registros = models.IntegerField('Registros', default=0)
    importado_em    = models.DateTimeField('Importado em', auto_now_add=True)
    importado_por   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                        null=True, blank=True, verbose_name='Usuário')

    class Meta:
        ordering = ['-importado_em']
        verbose_name = 'Log de Importação'
        verbose_name_plural = 'Logs de Importação'

    def __str__(self):
        return f'{self.get_tipo_display()} — {self.empreendimento} — {self.importado_em:%d/%m/%Y %H:%M}'
