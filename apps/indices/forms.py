# apps/indices/forms.py
from django import forms
from .models import Indice, IndiceData

class DateInput(forms.DateInput):
    input_type = 'date'

class DecimalInput(forms.NumberInput):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('attrs', {}).update({'step': '0.00000001'})
        super().__init__(*args, **kwargs)

class IndiceForm(forms.ModelForm):
    class Meta:
        model = Indice
        fields = ['descricao', 'periodo', 'calculo', 'tipo']
        widgets = {
            'descricao': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 40, 'autofocus': True}),
            'periodo': forms.Select(attrs={'class': 'form-select'}),
            'calculo': forms.Select(attrs={'class': 'form-select'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
        }

class IndiceDataForm(forms.ModelForm):
    class Meta:
        model = IndiceData
        fields = ['indice', 'data', 'valor']
        widgets = {
            'indice': forms.Select(attrs={'class': 'form-select'}),
            'data': DateInput(attrs={'class': 'form-control'}),
            'valor': DecimalInput(attrs={'class': 'form-control'}),
        }
