from django import forms
from .models import Product

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'category', 'unit', 'current_stock', 'safety_stock', 'lead_time_days', 'notes']
        widgets = {
            'name':           forms.TextInput(attrs={'placeholder': 'Ej: Arroz Blanco 1kg'}),
            'current_stock':  forms.NumberInput(attrs={'min': '0'}),
            'safety_stock':   forms.NumberInput(attrs={'min': '0'}),
            'lead_time_days': forms.NumberInput(attrs={'min': '1'}),
            'notes':          forms.TextInput(attrs={'placeholder': 'Ej: Proveedor Don Carlos...'}),
        }