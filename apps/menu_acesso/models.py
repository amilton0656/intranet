from django.db import models
from django.contrib.auth.models import User


class MenuItem(models.Model):
    APP_CHOICES = [
        ('intranet',      'Intranet'),
        ('bliss',         'Bliss Living'),
        ('cota365',       'Cota 365'),
        ('indices',       'Índices'),
        ('contratos',     'Contratos'),
        ('propostas',     'Propostas'),
        ('ajr_padrao',    'AJR Padrão'),
        ('incorporadora', 'Incorporadora'),
        ('maxflora',      'Max & Flora'),
        ('chat',          'Chat'),
    ]
    NAVBAR_CHOICES = [
        ('principal',  'Navbar Principal'),
        ('secundaria', 'Navbar Secundária'),
    ]

    app      = models.CharField('App', max_length=50, choices=APP_CHOICES)
    navbar   = models.CharField('Navbar', max_length=20, choices=NAVBAR_CHOICES)
    label    = models.CharField('Rótulo', max_length=100)
    url_name = models.CharField('URL name', max_length=200, blank=True)
    icon     = models.CharField('Ícone Bootstrap', max_length=60, blank=True)
    ordem    = models.PositiveSmallIntegerField('Ordem', default=0)
    ativo    = models.BooleanField('Ativo', default=True)
    grupo    = models.CharField('Grupo/Dropdown', max_length=50, blank=True,
                                help_text='Apenas para navbar principal: identifica o dropdown (ex: gerencial, financeiro, admin)')
    subgrupo = models.CharField('Sub-grupo', max_length=50, blank=True,
                                help_text='Apenas para Admin: identifica a seção dentro do dropdown (ex: incorporadora, contratos)')

    class Meta:
        ordering = ['app', 'navbar', 'ordem']
        verbose_name = 'Item de Menu'
        verbose_name_plural = 'Itens de Menu'

    def __str__(self):
        return f'{self.get_app_display()} › {self.get_navbar_display()} › {self.label}'


class EmpresaMenuItem(models.Model):
    """Itens de menu habilitados para uma empresa."""
    empresa   = models.ForeignKey(
        'incorporadora.Empresa',
        on_delete=models.CASCADE,
        related_name='menu_itens',
        verbose_name='Empresa',
    )
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name='empresas',
        verbose_name='Item de Menu',
    )
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        unique_together = [('empresa', 'menu_item')]
        ordering = ['empresa', 'menu_item__app', 'menu_item__navbar', 'menu_item__ordem']
        verbose_name = 'Item de Menu da Empresa'
        verbose_name_plural = 'Itens de Menu da Empresa'

    def __str__(self):
        return f'{self.empresa} › {self.menu_item.label}'


class UsuarioEmpresa(models.Model):
    """Usuário vinculado a uma empresa com seus itens de menu pessoais."""
    user    = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='empresas_acesso',
        verbose_name='Usuário',
    )
    empresa = models.ForeignKey(
        'incorporadora.Empresa',
        on_delete=models.CASCADE,
        related_name='usuarios_acesso',
        verbose_name='Empresa',
    )
    itens = models.ManyToManyField(
        MenuItem,
        blank=True,
        verbose_name='Itens habilitados',
        help_text='Subconjunto dos itens habilitados para a empresa.',
    )

    class Meta:
        unique_together = [('user', 'empresa')]
        verbose_name = 'Usuário da Empresa'
        verbose_name_plural = 'Usuários da Empresa'

    def __str__(self):
        return f'{self.user.username} @ {self.empresa}'
