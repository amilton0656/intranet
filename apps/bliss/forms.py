from django import forms
from .models import Bliss


class BlissForm(forms.ModelForm):
    class Meta:
        model = Bliss
        fields = [
            'bloco',
            'unidade',
            'perc_permuta',
            'area_privativa',
            'area_total',
            'garagem',
            'deposito',
            'tipologia',
            'situacao',
            'valor_tabela',
            'valor_venda',
            'data_venda',
            'cliente',
            'email',
        ]
        widgets = {
            'bloco': forms.TextInput(attrs={'class': 'form-control', 'autofocus': True, 'maxlength': 20}),
            'unidade': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 20}),
            'perc_permuta': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001', 'min': '0'}),
            'area_privativa': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'area_total': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'garagem': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 30}),
            'deposito': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 20}),
            'tipologia': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 20}),
            'situacao': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 30}),
            'valor_tabela': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'valor_venda': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'data_venda': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'cliente': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 100}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'maxlength': 100}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save(using='default')
        return instance
