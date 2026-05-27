from django import forms
from .models import Pessoa

_fc = {'class': 'form-control'}
_fs = {'class': 'form-select'}
_cb = {'class': 'form-check-input'}


class PessoaForm(forms.ModelForm):
    class Meta:
        model = Pessoa
        fields = [
            'tipo', 'nome', 'cpf_cnpj', 'rg_ie',
            'email', 'telefone', 'celular',
            'cep', 'logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'estado',
            'is_cliente', 'is_corretor', 'is_imobiliaria', 'is_fornecedor', 'is_outro',
            'observacoes', 'ativo',
        ]
        widgets = {
            'tipo':        forms.Select(attrs=_fs),
            'nome':        forms.TextInput(attrs={**_fc, 'autofocus': True}),
            'cpf_cnpj':    forms.TextInput(attrs=_fc),
            'rg_ie':       forms.TextInput(attrs=_fc),
            'email':       forms.EmailInput(attrs=_fc),
            'telefone':    forms.TextInput(attrs=_fc),
            'celular':     forms.TextInput(attrs=_fc),
            'cep':         forms.TextInput(attrs={**_fc, 'placeholder': '00000-000'}),
            'logradouro':  forms.TextInput(attrs=_fc),
            'numero':      forms.TextInput(attrs=_fc),
            'complemento': forms.TextInput(attrs=_fc),
            'bairro':      forms.TextInput(attrs=_fc),
            'cidade':      forms.TextInput(attrs=_fc),
            'estado':      forms.Select(attrs=_fs),
            'is_cliente':     forms.CheckboxInput(attrs=_cb),
            'is_corretor':    forms.CheckboxInput(attrs=_cb),
            'is_imobiliaria': forms.CheckboxInput(attrs=_cb),
            'is_fornecedor':  forms.CheckboxInput(attrs=_cb),
            'is_outro':       forms.CheckboxInput(attrs=_cb),
            'observacoes': forms.Textarea(attrs={**_fc, 'rows': 3}),
            'ativo':       forms.CheckboxInput(attrs=_cb),
        }
