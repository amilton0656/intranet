from django.db import models
from django.contrib.auth.models import User, Group


class MenuItem(models.Model):
    APP_CHOICES = [
        ('intranet',   'Intranet'),
        ('bliss',      'Bliss Living'),
        ('cota365',    'Cota 365'),
        ('indices',    'Índices'),
        ('contratos',  'Contratos'),
        ('propostas',  'Propostas'),
        ('ajr_padrao', 'AJR Padrão'),
        ('incorporadora', 'Incorporadora'),
        ('maxflora',   'Max & Flora'),
        ('chat',       'Chat'),
    ]

    NAVBAR_CHOICES = [
        ('principal',  'Navbar Principal'),
        ('secundaria', 'Navbar Secundária'),
    ]

    app    = models.CharField('App', max_length=50, choices=APP_CHOICES)
    navbar = models.CharField('Navbar', max_length=20, choices=NAVBAR_CHOICES)
    label  = models.CharField('Rótulo', max_length=100)
    url_name = models.CharField('URL name', max_length=200, blank=True,
                                help_text='Ex: bliss_resumo ou cota365:dashboard')
    icon   = models.CharField('Ícone Bootstrap', max_length=60, blank=True,
                              help_text='Ex: bi-speedometer2')
    ordem  = models.PositiveSmallIntegerField('Ordem', default=0)
    ativo  = models.BooleanField('Ativo', default=True)

    grupos   = models.ManyToManyField(Group, blank=True, related_name='menu_items',
                                      verbose_name='Grupos com acesso')
    usuarios = models.ManyToManyField(User, blank=True, related_name='menu_items',
                                      verbose_name='Usuários com acesso')

    class Meta:
        ordering = ['app', 'navbar', 'ordem']
        verbose_name = 'Item de Menu'
        verbose_name_plural = 'Itens de Menu'

    def __str__(self):
        return f'{self.get_app_display()} › {self.get_navbar_display()} › {self.label}'

    def tem_acesso(self, user):
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if self.usuarios.filter(pk=user.pk).exists():
            return True
        return self.grupos.filter(pk__in=user.groups.values_list('pk', flat=True)).exists()
