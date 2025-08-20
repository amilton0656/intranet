from django import forms
from .models import Bliss

class BlissForm(forms.ModelForm):
    class Meta:
        model = Bliss
        fields = '__all__'
