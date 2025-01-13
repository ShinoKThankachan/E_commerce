from django.shortcuts import render,redirect
from django.contrib.auth import authenticate,login,logout
from .models import *
import os
from django.contrib.auth.models import User
from django.contrib import messages

from django.core.mail import send_mail
from django.conf import settings 

# Create your views here.


def shp_login(req):
    if 'eshop' in req.session:
        return redirect(shp_home)
    if 'user' in req.session:
        return redirect(user_home)
    if req.method=='POST':
        uname=req.POST['uname']
        password=req.POST['pswd']
        data=authenticate(username=uname,password=password)
        if data:
            if data.is_superuser:
                login(req,data)
                req.session['eshop']=uname   #create session
                return redirect(shp_home)
            else:
                login(req,data)
                req.session['user']=uname   #create session
                return redirect(user_home)
        else:
            messages.warning(req,'Invalid username or password.')
            return redirect(shp_login)
    
    else:
        return render(req,'login.html')

def shp_home(req):
    if 'eshop' in req.session:
        data=Product.objects.all()
        return render(req,'shop/home.html',{'data':data})
    else:
        return redirect(shp_login)

def shp_logout(req):
    req.session.flush()          #delete session
    logout(req)
    return redirect(shp_login)

def add_prod(req):
    if 'eshop' in req.session:
        if req.method=='POST':
            prd_id=req.POST['prd_id']
            prd_name=req.POST['prd_name']
            prd_price=req.POST['prd_price']
            ofr_price=req.POST['ofr_price']
            img=req.FILES['img']
            prd_dis=req.POST['prd_dis']
            data=Product.objects.create(pro_id=prd_id,name=prd_name,price=prd_price,ofr_price=ofr_price,img=img,dis=prd_dis)
            data.save()
            return redirect(add_prod)
        else:
            return render(req,'shop/add_prod.html')
    else:
        return redirect(shp_login)
    
def edit_prod(req,pid):
    if 'eshop' in req.session:
        if req.method=='POST':
            prd_id=req.POST['prd_id']
            prd_name=req.POST['prd_name']
            prd_price=req.POST['prd_price']
            ofr_price=req.POST['ofr_price']
            prd_dis=req.POST['prd_dis']
            img=req.FILES.get('img')
            if img:
                Product.objects.filter(pk=pid).update(pro_id=prd_id,name=prd_name,price=prd_price,ofr_price=ofr_price,dis=prd_dis)
                data=Product.objects.get(pk=pid)
                data.img=img
                data.save()
            else:
                Product.objects.filter(pk=pid).update(pro_id=prd_id,name=prd_name,price=prd_price,ofr_price=ofr_price,dis=prd_dis)
            return redirect(shp_home)
        else:
            data=Product.objects.get(pk=pid)
            return render(req,'shop/edit.html',{'product':data})
    else:
        return redirect(shp_login)
def delete_prod(req,pid):
    data=Product.objects.get(pk=pid)
    url=data.img.url
    og_path=url.split('/')[-1]
    os.remove('media/'+og_path)
    data.delete()
    return redirect(shp_home)



def booking(req):
    buy=Buy.objects.all()[::-1]
    return render(req,'shop/booking.html',{'buy':buy})

#------------------------user--------------------------------

def register(req):
    if req.method=='POST':
        name=req.POST['name']
        email=req.POST['email']
        password=req.POST['password']
        send_mail('user registration','eshop account created', settings.EMAIL_HOST_USER, [email])
        try:
           
            data=User.objects.create_user(first_name=name,email=email,password=password,username=email)
            data.save()
            return redirect(shp_login)
        except:
            messages.warning(req,'User already exists.')
            return redirect(register)
    else:
        return render(req,'user/register.html')

def user_home(req):
    if 'user' in req.session:
        data=Product.objects.all()
        return render(req,'user/home.html',{'data':data})
    else:
        return redirect(shp_login)
    
def view_pro(req,pid):
    data=Product.objects.get(pk=pid)
    return render(req,'user/view_pro.html',{'data':data})

def add_to_cart(req,pid):
    prod=Product.objects.get(pk=pid)
    user=User.objects.get(username=req.session['user'])
    data=Cart.objects.create(user=user,product=prod)
    data.save()
    return redirect(view_cart)

def view_cart(req):
    user=User.objects.get(username=req.session['user'])
    cart_det=Cart.objects.filter(user=user)
    return render(req,'user/view_cart.html',{'cart_det':cart_det})

def delete_cart(req,id):
    cart=Cart.objects.get(pk=id)
    cart.delete()
    return redirect(view_cart) 

def user_buy(req,cid):
    user=User.objects.get(username=req.session['user'])
    cart=Cart.objects.get(pk=cid)
    product=cart.product
    price=cart.product.ofr_price
    buy=Buy.objects.create(user=user,product=product,price=price)
    buy.save()
    #cart.delete()
    return redirect(view_cart)

def user_buy1(req,pid):
    user=User.objects.get(username=req.session['user'])
    product=Product.objects.get(pk=pid) 
    price=product.ofr_price
    buy=Buy.objects.create(user=user,product=product,price=price)
    buy.save()
    return redirect(user_home)



def user_booking(req):
    user=User.objects.get(username=req.session['user'])
    buy=Buy.objects.filter(user=user)[::-1]
    return render(req,'user/booking.html',{'buy':buy})




