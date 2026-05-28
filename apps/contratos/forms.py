from django import forms
from .models import MinutaContrato

_fc = {'class': 'form-control'}
_fs = {'class': 'form-select'}
_cb = {'class': 'form-check-input'}


class MinutaContratoForm(forms.ModelForm):
    class Meta:
        model = MinutaContrato
        fields = ['nome', 'tipo', 'arquivo', 'descricao', 'ativo']
        widgets = {
            'nome':      forms.TextInput(attrs={**_fc, 'autofocus': True}),
            'tipo':      forms.Select(attrs=_fs),
            'arquivo':   forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={**_fc, 'rows': 3}),
            'ativo':     forms.CheckboxInput(attrs=_cb),
        }
