from django import forms
from .models import *

class QuantityForm(forms.Form):
    quantity = forms.IntegerField(initial=1, min_value=1)



class AddToCartForm(forms.ModelForm):
    quantity = forms.IntegerField(min_value=1, initial=1, label="Quantity")

    class Meta:
        model = CartItem
        fields = ['quantity']

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'stock', 'image', 'category']



class BillingAddressForm(forms.ModelForm):
    class Meta:
        model = BillingAddress
        fields = ['full_name', 'address_line', 'city', 'state', 'postal_code', 'country', 'phone_number']
