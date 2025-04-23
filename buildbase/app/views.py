from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.admin.views.decorators import staff_member_required
from .models import *
from django.http import HttpResponse
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from .forms import *


@login_required
def admin_home(request):
    if not request.user.is_superuser:
        return redirect('home')

    products = Product.objects.all()
    return render(request, 'admin/admin_home.html', {'products': products})


def home(request):
    products = Product.objects.all()
    return render(request, 'user/home.html', {'products': products})

def product_detail(request, product_id):
    product = Product.objects.get(id=product_id)
    if request.method == 'POST':
        return redirect('order_product', product_id=product.id)
    return render(request, 'user/product_detail.html', {'product': product})

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect(login_view)
    else:
        form = UserCreationForm()
    return render(request, 'user/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if user.is_superuser:
                return redirect('admin_home')
            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'user/login.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    return redirect(login_view)

@login_required
def order_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))

        # Store product and quantity in session temporarily
        request.session['pending_order'] = {
            'product_id': product.id,
            'quantity': quantity
        }
        print(f"Session 'pending_order' data: {request.session['pending_order']}")  # Debug print

        # Redirect to choose billing address
        return redirect('choose_billing_address_with_product', product_id=product.id)

    return render(request, 'user/order_product.html', {'product': product})


@login_required
def choose_billing_address(request, product_id=None):
    existing_addresses = BillingAddress.objects.filter(user=request.user)

    if request.method == 'POST':
        selected_address_id = request.POST.get('selected_address')

        if selected_address_id:
            # Use the existing selected address
            address = get_object_or_404(BillingAddress, id=selected_address_id, user=request.user)
        else:
            # Create a new address from the form
            form = BillingAddressForm(request.POST)
            if form.is_valid():
                address = form.save(commit=False)
                address.user = request.user
                address.save()
            else:
                return render(request, 'user/choose_billing_address.html', {
                    'form': form,
                    'existing_addresses': existing_addresses,
                    'product_id': product_id
                })

        # Store address ID in session
        request.session['billing_address_id'] = address.id
        print(f"Session 'billing_address_id': {request.session['billing_address_id']}")  # Debug print

        # Redirect to finalize order for the selected product
        return redirect('finalize_order_product', product_id=product_id)

    # GET request
    form = BillingAddressForm()
    return render(request, 'user/choose_billing_address.html', {
        'form': form,
        'existing_addresses': existing_addresses,
        'product_id': product_id
    })

@login_required
def finalize_order_product(request, product_id):
    # Fetch the pending order and billing address from session
    pending_order = request.session.get('pending_order')
    billing_address_id = request.session.get('billing_address_id')

    if not pending_order or not billing_address_id:
        return redirect('home')  # Redirect if something is missing (failsafe)

    print(f"Pending order session: {pending_order}")  # Debug print
    print(f"Billing address session: {billing_address_id}")  # Debug print

    billing_address = get_object_or_404(BillingAddress, id=billing_address_id, user=request.user)
    product = get_object_or_404(Product, id=pending_order['product_id'])
    quantity = pending_order.get('quantity', 1)

    # Create the order
    order = Order.objects.create(
        user=request.user,
        product=product,
        quantity=quantity,
        billing_address=billing_address
    )

    # Clear session data after creating the order
    del request.session['pending_order']
    del request.session['billing_address_id']

    # Redirect to the order detail page
    return redirect('order_detail', order_id=order.id)



@login_required
def order_detail(request, order_id):
    order = Order.objects.get(id=order_id)
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

            # Check if item is already in the cart
            cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)

            if not created:
                cart_item.quantity += quantity  # Update quantity if already exists
            else:
                cart_item.quantity = quantity

            cart_item.save()
            return redirect('view_cart')  # Redirect to cart page

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

    # Try to fetch an existing billing address (if user is logged in)
    user = request.user
    existing_address = BillingAddress.objects.filter(user=user).first()

    if request.method == 'POST':
        if existing_address:
            # Use the existing address for the order
            address = existing_address
        else:
            # If no address exists, create a new address
            form = BillingAddressForm(request.POST)
            if form.is_valid():
                new_address = form.save(commit=False)
                new_address.user = user
                new_address.save()
                address = new_address

        # Create an order after selecting or adding a billing address
        order = Order.objects.create(
            user=user,
            product=product,
            quantity=1,  # Assuming quantity is 1 for 'buy now'
            billing_address=address
        )

        # Redirect to the order detail page
        return redirect('order_detail', order_id=order.id)

    # If the user has an existing address, redirect them directly to the order detail page
    if existing_address:
        return redirect('order_product', product_id=product.id)

    # If no address exists, provide the form for the user to create one
    form = BillingAddressForm()
    return render(request, 'billing_address.html', {'form': form, 'product': product})



@login_required
def buy_all(request):
    # Get existing billing addresses for the user
    existing_addresses = BillingAddress.objects.filter(user=request.user)
    orders = Order.objects.filter(user=request.user)  # Adjust this as necessary

    # If the form is submitted via POST
    if request.method == 'POST':
        if 'selected_address' in request.POST:
            # If an existing address is selected
            selected_address = BillingAddress.objects.get(id=request.POST['selected_address'])
            # You can use this address for the order creation or updating existing orders
            # Example: associate with the user's current order
            # order.billing_address = selected_address
            # order.save()

            return redirect('order_detail', order_id=selected_address.order.id)  # Adjust accordingly

        # Handle new address creation
        else:
            form = BillingAddressForm(request.POST)
            if form.is_valid():
                new_address = form.save(commit=False)
                new_address.user = request.user  # Assign the logged-in user to the new address
                new_address.save()

                # Now, associate the new address with the user's orders or create a new order
                # Check if there are products in the cart to order
                cart = Cart.objects.get(user=request.user)
                cart_items = cart.items.all()

                if cart_items.exists():
                    # Create order for each item in the cart
                    for item in cart_items:
                        order = Order.objects.create(
                            user=request.user,
                            billing_address=new_address,
                            product=item.product,
                            quantity=item.quantity
                        )

                        # Optionally, clear the cart after the order is created
                        item.delete()

                    return redirect('order_summary')  # Redirect after successful submission
                else:
                    # Handle case if the cart is empty, e.g., show a message or redirect
                    return redirect('home')  # Or some error page for empty cart

    else:
        # Initialize form for new address
        form = BillingAddressForm()

    # Render the page with the form and existing addresses
    return render(request, 'user/buy_all.html', {
        'form': form,  # Pass the form to the template
        'orders': orders,  # Pass any other context needed
        'existing_addresses': existing_addresses,  # Pass existing addresses to the template
    })


@login_required
def order_summary(request):
    orders = Order.objects.filter(user=request.user).order_by('-id')  # Fetch all orders
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

