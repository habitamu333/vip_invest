from django import forms
from .models import Deposit

class DepositForm(forms.ModelForm):
    class Meta:
        model = Deposit
        fields = ['amount', 'payment_method', 'proof']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter deposit amount'
            }),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'proof': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }