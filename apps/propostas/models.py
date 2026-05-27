from django.db import models
from django.utils import timezone


def _upload_documento(instance, filename):
    return f'propostas/{instance.proposta.numero}/{filename}'


class Proposta(models.Model):
    SITUACAO_CHOICES = [
        ('rascunho',           'Rascunho'),
        ('enviada',            'Enviada'),
        ('em_analise',         'Em Análise'),
        ('aprovada',           'Aprovada'),
        ('reprovada',          'Reprovada'),
        ('contrato_elaborado', 'Contrato Elaborado'),
        ('contratada',         'Contratada'),
    ]

    numero          = models.CharField('Número', max_length=20, unique=True, editable=False)
    situacao        = models.CharField('Situação', max_length=30, choices=SITUACAO_CHOICES, default='rascunho', db_index=True)
    data            = models.DateField('Data', default=timezone.now)
    numero_contrato = models.CharField('Nº Contrato', max_length=30, blank=True)

    imobiliaria = models.ForeignKey(
        'pessoas.Pessoa', on_delete=models.PROTECT,
        related_name='propostas_imobiliaria', verbose_name='Imobiliária',
        limit_choices_to={'is_imobiliaria': True},
    )
    corretor = models.ForeignKey(
        'pessoas.Pessoa', on_delete=models.PROTECT,
        related_name='propostas_corretor', verbose_name='Corretor',
        limit_choices_to={'is_corretor': True},
    )
    empreendimento = models.ForeignKey(
        'incorporadora.Empreendimento', on_delete=models.PROTECT,
        related_name='propostas', verbose_name='Empreendimento',
    )
    tabela = models.ForeignKey(
        'incorporadora.TabelaVendas', on_delete=models.PROTECT,
        related_name='propostas', verbose_name='Tabela de Vendas',
    )
    observacoes = models.TextField('Observações', blank=True)

    criado_em     = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'Proposta'
        verbose_name_plural = 'Propostas'

    def __str__(self):
        return self.numero

    def save(self, *args, **kwargs):
        if not self.numero:
            ano = timezone.now().year
            ultimo = (Proposta.objects
                      .filter(numero__startswith=f'PROP-{ano}-')
                      .order_by('-numero')
                      .first())
            if ultimo:
                try:
                    seq = int(ultimo.numero.split('-')[-1]) + 1
                except ValueError:
                    seq = 1
            else:
                seq = 1
            self.numero = f'PROP-{ano}-{seq:04d}'
        super().save(*args, **kwargs)

    @property
    def valor_tabela_total(self):
        return sum(s.subtotal for s in self.series.filter(origem='tabela'))

    @property
    def valor_proposto_total(self):
        return sum(s.subtotal for s in self.series.filter(origem='proposta'))


class UnidadeProposta(models.Model):
    proposta = models.ForeignKey(Proposta, on_delete=models.CASCADE, related_name='unidades', verbose_name='Proposta')
    unidade  = models.ForeignKey('incorporadora.Unidade', on_delete=models.PROTECT, related_name='propostas', verbose_name='Unidade')

    class Meta:
        ordering = ['unidade__bloco__nome', 'unidade__numero']
        unique_together = [('proposta', 'unidade')]
        verbose_name = 'Unidade da Proposta'
        verbose_name_plural = 'Unidades da Proposta'

    def __str__(self):
        return f'{self.proposta.numero} — {self.unidade}'


class ParticipanteProposta(models.Model):
    PAPEL_CHOICES = [
        ('proponente',    'Proponente'),
        ('interveniente', 'Interveniente'),
        ('coobrigado',    'Coobrigado'),
    ]

    proposta = models.ForeignKey(Proposta, on_delete=models.CASCADE, related_name='participantes', verbose_name='Proposta')
    pessoa   = models.ForeignKey('pessoas.Pessoa', on_delete=models.PROTECT, related_name='participacoes_proposta', verbose_name='Pessoa')
    papel    = models.CharField('Papel', max_length=20, choices=PAPEL_CHOICES)

    class Meta:
        ordering = ['papel', 'pessoa__nome']
        verbose_name = 'Participante da Proposta'
        verbose_name_plural = 'Participantes da Proposta'

    def __str__(self):
        return f'{self.get_papel_display()}: {self.pessoa.nome}'


class SerieProposta(models.Model):
    ORIGEM_CHOICES = [
        ('tabela',   'Tabela de Vendas'),
        ('proposta', 'Proposta'),
    ]
    TIPO_CHOICES = [
        ('fixa',     'Fixa'),
        ('variavel', 'Variável'),
    ]
    INDEXADOR_CHOICES = [
        ('nenhum',          'Nenhum'),
        ('cub_residencial', 'CUB Residencial'),
        ('cub_comercial',   'CUB Comercial'),
        ('incc',            'INCC'),
        ('igpm',            'IGP-M'),
        ('ipca',            'IPCA'),
    ]

    proposta            = models.ForeignKey(Proposta, on_delete=models.CASCADE, related_name='series', verbose_name='Proposta')
    origem              = models.CharField('Origem', max_length=10, choices=ORIGEM_CHOICES, db_index=True)
    label               = models.CharField('Série', max_length=100)
    tipo                = models.CharField('Tipo', max_length=10, choices=TIPO_CHOICES, default='fixa')
    quantidade          = models.PositiveIntegerField('Parcelas', default=1)
    valor               = models.DecimalField('Valor (R$)', max_digits=14, decimal_places=2, default=0)
    primeiro_vencimento = models.DateField('1º Vencimento', null=True, blank=True)
    indexador           = models.CharField('Indexador', max_length=20, choices=INDEXADOR_CHOICES, default='nenhum')
    ordem               = models.PositiveSmallIntegerField('Ordem', default=0)

    class Meta:
        ordering = ['origem', 'ordem', 'primeiro_vencimento']
        verbose_name = 'Série da Proposta'
        verbose_name_plural = 'Séries da Proposta'

    def __str__(self):
        return f'{self.proposta.numero} — {self.label} ({self.get_origem_display()})'

    @property
    def subtotal(self):
        return self.valor * self.quantidade


class DocumentoProposta(models.Model):
    TIPO_CHOICES = [
        ('rg',                     'RG'),
        ('cpf',                    'CPF'),
        ('comprovante_renda',      'Comprovante de Renda'),
        ('extrato_bancario',       'Extrato Bancário'),
        ('comprovante_residencia', 'Comprovante de Residência'),
        ('certidao',               'Certidão'),
        ('outro',                  'Outro'),
    ]

    proposta     = models.ForeignKey(Proposta, on_delete=models.CASCADE, related_name='documentos', verbose_name='Proposta')
    participante = models.ForeignKey(ParticipanteProposta, on_delete=models.SET_NULL, null=True, blank=True, related_name='documentos', verbose_name='Participante')
    tipo         = models.CharField('Tipo', max_length=30, choices=TIPO_CHOICES, default='outro')
    arquivo      = models.FileField('Arquivo', upload_to=_upload_documento)
    descricao    = models.CharField('Descrição', max_length=255, blank=True)
    uploaded_em  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['participante__pessoa__nome', 'tipo']
        verbose_name = 'Documento da Proposta'
        verbose_name_plural = 'Documentos da Proposta'

    def __str__(self):
        return f'{self.proposta.numero} — {self.get_tipo_display()}'
