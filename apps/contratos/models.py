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

    nome     = models.CharField('Nome', max_length=100)
    tipo     = models.CharField('Tipo', max_length=20, choices=TIPO_CHOICES, default='parcelado')
    arquivo  = models.FileField('Arquivo (.docx)', upload_to='minutas/')
    descricao = models.TextField('Descrição', blank=True)
    ativo    = models.BooleanField('Ativo', default=True)

    criado_em   = models.DateTimeField(auto_now_add=True)
    alterado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'Minuta de Contrato'
        verbose_name_plural = 'Minutas de Contrato'

    def __str__(self):
        return self.nome


@receiver(post_delete, sender=MinutaContrato)
def _deletar_arquivo_ao_excluir(sender, instance, **kwargs):
    if instance.arquivo:
        instance.arquivo.delete(save=False)


@receiver(pre_save, sender=MinutaContrato)
def _deletar_arquivo_ao_substituir(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        anterior = MinutaContrato.objects.get(pk=instance.pk)
    except MinutaContrato.DoesNotExist:
        return
    if anterior.arquivo and anterior.arquivo != instance.arquivo:
        anterior.arquivo.delete(save=False)
