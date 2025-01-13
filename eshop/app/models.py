from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Product(models.Model):
    pro_id=models.TextField()
    name=models.TextField()
    price=models.IntegerField()
    ofr_price=models.IntegerField()
    img=models.FileField()
    dis=models.TextField()

class Cart(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE)
    product=models.ForeignKey(Product,on_delete=models.CASCADE)

class Buy(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE)
    product=models.ForeignKey(Product,on_delete=models.CASCADE)
    price=models.IntegerField()
    data=models.DateField(auto_now_add=True)