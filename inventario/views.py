from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Product
from .forms import ProductForm
from django.db import models

@login_required
def dashboard(request):
    return render(request, 'inventario/dashboard.html')

@login_required
def products_list(request):
    products = Product.objects.filter(user=request.user, is_active=True)
    form = ProductForm()

    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.user = request.user
            product.save()
            messages.success(request, f'✅ Producto "{product.name}" guardado correctamente.')
            return redirect('products_list')
        else:
            messages.error(request, '⚠️ Revisa los campos obligatorios.')

    return render(request, 'inventario/products.html', {
        'products': products,
        'form': form,
    })