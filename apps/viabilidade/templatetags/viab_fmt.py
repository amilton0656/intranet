from django import template

register = template.Library()


def _br(value, decimals):
    try:
        val = float(value) if value is not None else 0.0
        # f"{val:,.Nf}" → "12,802.95" (English) → swap separators → "12.802,95"
        eng = f"{val:,.{decimals}f}"
        return eng.replace(',', 'X').replace('.', ',').replace('X', '.')
    except (TypeError, ValueError):
        return '0,' + '0' * decimals


@register.filter
def br2(value):
    """Format with 2 decimal places: 12.802,95"""
    return _br(value, 2)


@register.filter
def br4(value):
    """Format with 4 decimal places: 12.802,9500"""
    return _br(value, 4)


@register.filter
def br0(value):
    """Format with 0 decimal places: 12.803"""
    return _br(value, 0)
