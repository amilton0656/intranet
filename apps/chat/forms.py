from django import forms


class ChatForm(forms.Form):
    document = forms.FileField(
        required=False,
        label='Documento',
        help_text='Envie um arquivo (.txt ou .pdf) para indexar o conteudo.',
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'}),
    )
    question = forms.CharField(
        required=False,
        label='Pergunta',
        widget=forms.Textarea(
            attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Digite sua pergunta sobre o documento carregado...',
            }
        ),
    )

    def clean(self):
        cleaned_data = super().clean()
        document = cleaned_data.get('document')
        question = cleaned_data.get('question')

        if not document and not question:
            raise forms.ValidationError(
                'Envie um documento ou faca uma pergunta relacionada a um documento ja carregado.'
            )

        return cleaned_data


class BlissMemorialForm(forms.Form):
    question = forms.CharField(
        required=True,
        label='Pergunta',
        widget=forms.Textarea(
            attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Digite sua pergunta sobre o memorial Bliss...',
            }
        ),
    )
