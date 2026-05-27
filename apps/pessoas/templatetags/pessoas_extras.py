import re
from django import template

register = template.Library()


@register.filter
def fmt_cpf_cnpj(value):
    if not value:
        return '—'
    digits = re.sub(r'\D', '', str(value))
    if len(digits) == 11:
        return f'{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}'
    if len(digits) == 14:
        return f'{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}'
    return value


@register.filter
def fmt_fone(value):
    if not value:
        return '—'
    digits = re.sub(r'\D', '', str(value))
    if len(digits) == 11:
        return f'({digits[:2]}) {digits[2:7]}-{digits[7:]}'
    if len(digits) == 10:
        return f'({digits[:2]}) {digits[2:6]}-{digits[6:]}'
    return value
