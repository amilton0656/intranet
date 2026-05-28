from django.conf import settings
from django.db import models
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver


class MinutaContrato(models.Model):
    TIPO_CHOICES = [
        ('avista',    'À Vista'),
        ('parcelado', 'Parcelado'),
        ('permuta',   'Permuta'),
        ('outro',     'Outro'),
    ]

    nome      = models.CharField('Nome', max_length=100)
    tipo      = models.CharField('Tipo', max_length=20, choices=TIPO_CHOICES, default='parcelado')
    arquivo   = models.FileField('Arquivo (.docx)', upload_to='minutas/')
    descricao = models.TextField('Descrição', blank=True)
    ativo     = models.BooleanField('Ativo', default=True)

    criado_em   = models.DateTimeField(auto_now_add=True)
    alterado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'Minuta de Contrato'
        verbose_name_plural = 'Minutas de Contrato'

    def __str__(self):
        return self.nome


def _upload_contrato(instance, filename):
    return f'contratos/{instance.proposta.numero}/{filename}'


class ContratoGerado(models.Model):
    proposta   = models.ForeignKey(
        'propostas.Proposta', on_delete=models.CASCADE,
        related_name='contratos_gerados', verbose_name='Proposta',
    )
    minuta     = models.ForeignKey(
        MinutaContrato, on_delete=models.PROTECT,
        related_name='contratos_gerados', verbose_name='Minuta',
    )
    arquivo    = models.FileField('Arquivo', upload_to=_upload_contrato)
    gerado_em  = models.DateTimeField(auto_now_add=True)
    gerado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='Gerado por',
    )

    class Meta:
        ordering = ['-gerado_em']
        verbose_name = 'Contrato Gerado'
        verbose_name_plural = 'Contratos Gerados'

    def __str__(self):
        return f'{self.proposta.numero} — {self.minuta.nome} ({self.gerado_em:%d/%m/%Y})'

    @property
    def nome_arquivo(self):
        return self.arquivo.name.split('/')[-1] if self.arquivo else ''


# ── Signals ───────────────────────────────────────────────────────────────────

@receiver(post_delete, sender=MinutaContrato)
def _deletar_minuta_ao_excluir(sender, instance, **kwargs):
    if instance.arquivo:
        instance.arquivo.delete(save=False)


@receiver(pre_save, sender=MinutaContrato)
def _deletar_minuta_ao_substituir(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        anterior = MinutaContrato.objects.get(pk=instance.pk)
    except MinutaContrato.DoesNotExist:
        return
    if anterior.arquivo and anterior.arquivo != instance.arquivo:
        anterior.arquivo.delete(save=False)


@receiver(post_delete, sender=ContratoGerado)
def _deletar_contrato_ao_excluir(sender, instance, **kwargs):
    if instance.arquivo:
        instance.arquivo.delete(save=False)
