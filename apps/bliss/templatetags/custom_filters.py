from django import template
from decimal import Decimal, InvalidOperation

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


@register.filter(name='format_number_ptbr')
def format_number_ptbr(value, decimal_places=2):
    try:
        decimal_places = int(decimal_places)
    except (TypeError, ValueError):
        decimal_places = 2

    try:
        amount = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return ('0,' + '0' * decimal_places) if decimal_places else '0'

    if decimal_places == 0:
        quantized = amount.quantize(Decimal('1'))
        formatted = f"{quantized:,}"
    else:
        quantize_str = '0.' + '0' * (decimal_places - 1) + '1'
        quantized = amount.quantize(Decimal(quantize_str))
        formatted = f"{quantized:,.{decimal_places}f}"

    formatted = formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
    return formatted

