from django import template

register = template.Library()


def _fmt(value, places):
    try:
        v = float(value)
        s = f'{v:,.{places}f}'
        return s.replace(',', 'X').replace('.', ',').replace('X', '.')
    except (TypeError, ValueError):
        return str(value) if value is not None else ''


@register.filter
def brl(value):
    """Formata como moeda brasileira: R$ 1.234,56"""
    return 'R$ ' + _fmt(value, 2)


@register.filter
def dec(value, places=2):
    """Formata decimal no padrão brasileiro: 1.234,56"""
    return _fmt(value, int(places))
