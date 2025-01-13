from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Product, Order
from django.http import HttpResponse

# Admin views
def admin_home(request):
    return render(request, 'admin/admin_home.html')

# User views
def home(request):
    products = Product.objects.all()
    return render(request, 'user/home.html', {'products': products})

def product_detail(request, product_id):
    product = Product.objects.get(id=product_id)
    return render(request, 'user/product_detail.html', {'product': product})

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'user/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'user/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')

def order_product(request, product_id):
    product = Product.objects.get(id=product_id)
    if request.method == 'POST':
        quantity = int(request.POST['quantity'])
        order = Order.objects.create(user=request.user, product=product, quantity=quantity)
        order.save()
        return redirect('order_detail', order_id=order.id)
    return render(request, 'user/order_product.html', {'product': product})

def order_detail(request, order_id):
    order = Order.objects.get(id=order_id)
    return render(request, 'user/order_detail.html', {'order': order})

def user_orders(request):
    orders = Order.objects.filter(user=request.user)
    return render(request, 'user/user_orders.html', {'orders': orders})

