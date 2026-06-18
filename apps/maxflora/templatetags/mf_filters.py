from django import template

register = template.Library()


@register.filter
def brl(value):
    """Formata número como moeda brasileira: R$ 1.234.567,89"""
    if value is None:
        return ''
    try:
        v = float(value)
    except (TypeError, ValueError):
        return ''
    formatted = f'{v:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    return f'R$\xa0{formatted}'


@register.filter
def brl_m2(value):
    """Formata m² com vírgula decimal: 1.234,56"""
    if value is None:
        return ''
    try:
        return f'{float(value):,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    except (TypeError, ValueError):
        return ''
