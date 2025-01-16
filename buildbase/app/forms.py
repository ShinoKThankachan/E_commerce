from django import forms

class QuantityForm(forms.Form):
    quantity = forms.IntegerField(initial=1, min_value=1)
