from django.urls import path
from . import views

urlpatterns = [
    path('admin/', views.admin_home, name='admin_home'),
    path('', views.home, name='home'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('order/<int:product_id>/', views.order_product, name='order_product'),
    path('order/detail/<int:order_id>/', views.order_detail, name='order_detail'),
    path('user/orders/', views.user_orders, name='user_orders'),
]