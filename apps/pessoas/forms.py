from django import forms
from .models import Pessoa

_fc = {'class': 'form-control'}
_fs = {'class': 'form-select'}
_cb = {'class': 'form-check-input'}


class PessoaForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['representante'].queryset = Pessoa.objects.filter(tipo='fisica').order_by('nome')
        self.fields['representante'].empty_label = '— Selecione —'

    class Meta:
        model = Pessoa
        fields = [
            'tipo', 'nome', 'cpf_cnpj', 'rg_ie', 'rg_orgao_emissor',
            'nacionalidade', 'profissao', 'estado_civil', 'regime_bens',
            'tipo_societario', 'representante',
            'email', 'telefone', 'celular',
            'cep', 'logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'estado',
            'banco_nome', 'banco_agencia', 'banco_conta', 'banco_tipo_conta',
            'is_cliente', 'is_corretor', 'is_imobiliaria', 'is_fornecedor', 'is_outro',
            'observacoes', 'ativo',
        ]
        widgets = {
            'tipo':             forms.Select(attrs=_fs),
            'nome':             forms.TextInput(attrs={**_fc, 'autofocus': True}),
            'cpf_cnpj':         forms.TextInput(attrs=_fc),
            'rg_ie':            forms.TextInput(attrs=_fc),
            'rg_orgao_emissor': forms.TextInput(attrs={**_fc, 'placeholder': 'Ex: SSP/SP'}),
            'nacionalidade':    forms.TextInput(attrs=_fc),
            'profissao':        forms.TextInput(attrs=_fc),
            'estado_civil':     forms.Select(attrs=_fs),
            'regime_bens':      forms.Select(attrs=_fs),
            'tipo_societario':  forms.TextInput(attrs={**_fc, 'placeholder': 'Ex: Ltda, S/A, MEI'}),
            'representante':    forms.Select(attrs=_fs),
            'email':            forms.EmailInput(attrs=_fc),
            'telefone':         forms.TextInput(attrs=_fc),
            'celular':          forms.TextInput(attrs=_fc),
            'cep':              forms.TextInput(attrs={**_fc, 'placeholder': '00000-000'}),
            'logradouro':       forms.TextInput(attrs=_fc),
            'numero':           forms.TextInput(attrs=_fc),
            'complemento':      forms.TextInput(attrs=_fc),
            'bairro':           forms.TextInput(attrs=_fc),
            'cidade':           forms.TextInput(attrs=_fc),
            'estado':           forms.Select(attrs=_fs),
            'banco_nome':       forms.TextInput(attrs=_fc),
            'banco_agencia':    forms.TextInput(attrs=_fc),
            'banco_conta':      forms.TextInput(attrs=_fc),
            'banco_tipo_conta': forms.Select(attrs=_fs),
            'is_cliente':       forms.CheckboxInput(attrs=_cb),
            'is_corretor':      forms.CheckboxInput(attrs=_cb),
            'is_imobiliaria':   forms.CheckboxInput(attrs=_cb),
            'is_fornecedor':    forms.CheckboxInput(attrs=_cb),
            'is_outro':         forms.CheckboxInput(attrs=_cb),
            'observacoes':      forms.Textarea(attrs={**_fc, 'rows': 3}),
            'ativo':            forms.CheckboxInput(attrs=_cb),
        }
