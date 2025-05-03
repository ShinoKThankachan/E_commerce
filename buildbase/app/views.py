from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.admin.views.decorators import staff_member_required
from .models import *
import random
from django.core.mail import send_mail
from django.contrib import messages
from django.http import HttpResponse
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from .forms import *
from django.conf import settings
from django.contrib import auth
import razorpay
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta
from django.utils import timezone


def home(request):
    products = Product.objects.all()
    return render(request, 'user/home.html', {'products': products})

@login_required
def admin_home(request):
    if not request.user.is_superuser:
        return redirect('home')
    products = Product.objects.all()
    return render(request, 'admin/admin_home.html', {'products': products})


def product_detail(request, product_id):
    product = Product.objects.get(id=product_id)
    if request.method == 'POST':
        return redirect('order_product', product_id=product.id)
    return render(request, 'user/product_detail.html', {'product': product})

def register(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        confpassword = request.POST['confpassword']

        if password != confpassword:
            messages.error(request, "Passwords do not match.")
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect('register')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already in use.")
            return redirect('register')

        user = User.objects.create_user(username=username, email=email, password=password)
        user.save()
        messages.success(request, "Registration successful. Please login.")
        return redirect('login')

    return render(request, 'user/register.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = auth.authenticate(username=username, password=password)
        if user is not None:
            auth.login(request, user)

            if user.is_superuser:
                return redirect('admin_home')  
            else:
                return redirect('home')
        else:
            messages.error(request, "Invalid credentials")
            return redirect('login')

    return render(request, 'user/login.html')
@login_required
def logout_view(request):
    logout(request)
    return redirect(login_view)

@login_required
def order_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        request.session['pending_order'] = {'product_id': product.id, 'quantity': quantity}
        return redirect('choose_billing_address', product_id=product.id)
    return render(request, 'user/order_product.html', {'product': product})


@login_required
def choose_billing_address(request, product_id=None):
    existing_addresses = BillingAddress.objects.filter(user=request.user)
    if request.method == 'POST':
        selected_address_id = request.POST.get('selected_address')
        if selected_address_id:
            address = get_object_or_404(BillingAddress, id=selected_address_id, user=request.user)
        else:
            form = BillingAddressForm(request.POST)
            if form.is_valid():
                address = form.save(commit=False)
                address.user = request.user
                address.save()
            else:
                return render(request, 'user/choose_billing_address.html', {
                    'form': form, 'existing_addresses': existing_addresses, 'product_id': product_id
                })
        request.session['billing_address_id'] = address.id
        return redirect('start_payment', product_id=product_id)
    form = BillingAddressForm()
    return render(request, 'user/choose_billing_address.html', {
        'form': form, 'existing_addresses': existing_addresses, 'product_id': product_id
    })


@login_required
def finalize_order_product(request, product_id):
    pending_order = request.session.get('pending_order')
    billing_address_id = request.session.get('billing_address_id')
    if not pending_order or not billing_address_id:
        return redirect('home')
    billing_address = get_object_or_404(BillingAddress, id=billing_address_id, user=request.user)
    product = get_object_or_404(Product, id=pending_order['product_id'])
    quantity = pending_order.get('quantity', 1)
    order = Order.objects.create(user=request.user, product=product, quantity=quantity, billing_address=billing_address)
    del request.session['pending_order']
    del request.session['billing_address_id']
    return redirect('order_detail', order_id=order.id)

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'user/order_detail.html', {'order': order})


@login_required
def user_orders(request):
    orders = Order.objects.filter(user=request.user)
    return render(request, 'user/user_orders.html', {'orders': orders})

@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart, created = Cart.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = AddToCartForm(request.POST)
        if form.is_valid():
            quantity = form.cleaned_data['quantity']
            cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
            if not created:
                cart_item.quantity += quantity
            else:
                cart_item.quantity = quantity
            cart_item.save()
            return redirect('view_cart')
    else:
        form = AddToCartForm()
    return render(request, 'user/add_to_cart.html', {'form': form, 'product': product})

@login_required
def view_cart(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()
    total_price = cart.get_total_price()
    return render(request, 'user/view_cart.html', {'cart_items': cart_items, 'total_price': total_price})

@login_required
def remove_from_cart(request, product_id):
    cart = Cart.objects.get(user=request.user)
    product = get_object_or_404(Product, id=product_id)
    cart_item = get_object_or_404(CartItem, cart=cart, product=product)
    cart_item.delete()
    return redirect('view_cart')

@login_required
def update_cart(request, product_id):
    if request.method == "POST":
        product = get_object_or_404(Product, id=product_id)
        quantity = int(request.POST.get("quantity", 1))
        cart_item, created = CartItem.objects.get_or_create(product=product, user=request.user)
        cart_item.quantity = quantity
        cart_item.total_price = quantity * product.price
        cart_item.save()
        return JsonResponse({"message": "Product added to cart!", "total_price": cart_item.total_price})
    return JsonResponse({"error": "Invalid request"}, status=400)

@login_required
def buy_now(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    user = request.user
    existing_address = BillingAddress.objects.filter(user=user).first()
    if request.method == 'POST':
        if existing_address:
            address = existing_address
        else:
            form = BillingAddressForm(request.POST)
            if form.is_valid():
                new_address = form.save(commit=False)
                new_address.user = user
                new_address.save()
                address = new_address
        order = Order.objects.create(user=user, product=product, quantity=1, billing_address=address)
        return redirect('order_detail', order_id=order.id)
    if existing_address:
        return redirect('order_product', product_id=product.id)
    form = BillingAddressForm()
    return render(request, 'billing_address.html', {'form': form, 'product': product})

@login_required
def buy_all(request):
    existing_addresses = BillingAddress.objects.filter(user=request.user)
    orders = Order.objects.filter(user=request.user)
    if request.method == 'POST':
        if 'selected_address' in request.POST:
            selected_address = BillingAddress.objects.get(id=request.POST['selected_address'])
            return redirect('order_detail', order_id=selected_address.order.id)
        else:
            form = BillingAddressForm(request.POST)
            if form.is_valid():
                new_address = form.save(commit=False)
                new_address.user = request.user
                new_address.save()
                cart = Cart.objects.get(user=request.user)
                cart_items = cart.items.all()
                if cart_items.exists():
                    for item in cart_items:
                        order = Order.objects.create(user=request.user, billing_address=new_address, product=item.product, quantity=item.quantity)
                        item.delete()
                    return redirect('order_summary')
                else:
                    return redirect('home')
    else:
        form = BillingAddressForm()
    return render(request, 'user/buy_all.html', {
        'form': form, 'orders': orders, 'existing_addresses': existing_addresses,
    })

@login_required
def order_summary(request):
    orders = Order.objects.filter(user=request.user).order_by('-id')
    return render(request, 'user/order_summary.html', {'orders': orders})

@staff_member_required
def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('admin_home')
    else:
        form = ProductForm()
    return render(request, 'admin/add_product.html', {'form': form})

@login_required
def edit_product(request, product_id):
    if not request.user.is_superuser:
        return redirect('home')
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return redirect('admin_home')
    else:
        form = ProductForm(instance=product)
    return render(request, 'admin/edit_product.html', {'form': form})

@login_required
def delete_product(request, product_id):
    if not request.user.is_superuser:
        return redirect('home')
    product = get_object_or_404(Product, id=product_id)
    product.delete()
    return redirect('admin_home')

@login_required
def view_all_orders(request):
    if not request.user.is_superuser:
        return redirect('home')
    orders = Order.objects.all().order_by('-ordered_at')
    return render(request, 'admin/all_orders.html', {'orders': orders})

razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

@login_required
def start_payment(request, product_id):
    pending_order = request.session.get('pending_order')
    billing_address_id = request.session.get('billing_address_id')
    if not pending_order or not billing_address_id:
        return redirect('home')
    product = get_object_or_404(Product, id=product_id)
    quantity = pending_order.get('quantity', 1)
    amount = int(product.price * quantity * 100)
    razorpay_order = razorpay_client.order.create(dict(
        amount=amount, currency='INR', payment_capture=1
    ))
    request.session['razorpay_order_id'] = razorpay_order['id']
    context = {
        'product': product, 'quantity': quantity, 'amount': amount,
        'api_key': settings.RAZORPAY_KEY_ID, 'order_id': razorpay_order['id'],
        'user': request.user,
    }
    return render(request, 'payment/checkout.html', context)

@csrf_exempt
@login_required
def payment_success(request):
    if request.method == "POST":
        params_dict = {
            'razorpay_order_id': request.POST.get('razorpay_order_id'),
            'razorpay_payment_id': request.POST.get('razorpay_payment_id'),
            'razorpay_signature': request.POST.get('razorpay_signature')
        }
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        try:
            client.utility.verify_payment_signature(params_dict)
        except razorpay.errors.SignatureVerificationError:
            return HttpResponse("Payment Verification Failed", status=400)
       
        pending_order = request.session.get('pending_order')
        billing_address_id = request.session.get('billing_address_id')
        razorpay_order_id = request.session.get('razorpay_order_id')
        if not pending_order or not billing_address_id or not razorpay_order_id:
            return redirect('home')
        billing_address = get_object_or_404(BillingAddress, id=billing_address_id, user=request.user)
        product = get_object_or_404(Product, id=pending_order['product_id'])
        quantity = pending_order.get('quantity', 1)
        amount = int(product.price * quantity * 100)
        order = Order.objects.create(
            user=request.user, product=product, quantity=quantity, amount=amount,
            billing_address=billing_address, razorpay_order_id=params_dict['razorpay_order_id'],
            razorpay_payment_id=params_dict['razorpay_payment_id'],
            razorpay_signature=params_dict['razorpay_signature'], status='Paid'
        )
    
        del request.session['pending_order']
        del request.session['billing_address_id']
        del request.session['razorpay_order_id']
        
        return redirect('order_detail', order_id=order.id)
    return redirect('home')

def forgot_password_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        otp = random.randint(100000, 999999)

        request.session['reset_email'] = email
        request.session['otp'] = otp

        send_mail(
            subject='Your OTP Code',
            message=f'Your OTP is {otp}',
            from_email='youremail@example.com',
            recipient_list=[email],
            fail_silently=False,
        )

        messages.success(request, 'OTP has been sent to your email.')
        return redirect('verify_otp')

    return render(request, 'user/forgot_password.html')

def verify_otp(request):
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        if str(request.session.get('otp')) == entered_otp:
            messages.success(request, 'OTP verified. You can now reset your password.')
            return redirect('reset_password')
        else:
            messages.error(request, 'Invalid OTP. Please try again.')

    return render(request, 'user/verify_otp.html')


# Password Reset View
def reset_password(request):
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        email = request.session.get('reset_email')

        user = User.objects.filter(email=email).first()
        if user:
            user.set_password(new_password)
            user.save()
            messages.success(request, "Password has been reset. You can now log in.")
            return redirect('login')
        else:
            messages.error(request, "Something went wrong. Please try again.")
            return redirect('forgot_password')

    return render(request, 'user/reset_password.html')