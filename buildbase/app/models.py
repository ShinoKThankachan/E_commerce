from django.db import models
from django.contrib.auth.models import User

class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField()
    image = models.ImageField(upload_to='products/')
    category = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    ordered_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=100, default="Pending")

    def __str__(self):
        return f"Order by {self.user.username} for {self.product.name}"


def save(self, *args, **kwargs):
        if self.pk is None:  
            product = self.product
            if product.stock_quantity >= self.quantity:
                product.stock_quantity -= self.quantity
                product.save()
            else:
                raise ValueError("Not enough stock available")
        super().save(*args, **kwargs)
