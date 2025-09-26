from django import template

register = template.Library()

@register.filter(name='format_real')
def format_real(value):
    try:
        valor = float(value)
        return f'R$ {valor:,.2f}'.replace(",", "v").replace(".", ",").replace("v", ".")
    except (ValueError, TypeError):
        return 'R$ 0,00'

@register.filter(name='has_group')
def has_group(user, group_name):
    if not hasattr(user, 'groups'):
        return False
    return user.groups.filter(name=group_name).exists()

