from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
from django.utils import timezone
from .models import Product, Sale
from .forms import ProductForm
from .calculator import calculate_recommendation
from .models import Product, Sale, Recommendation

@login_required
def dashboard(request):
    products = Product.objects.filter(user=request.user, is_active=True)
    recomendaciones = [calculate_recommendation(p) for p in products]
    urgentes   = [r for r in recomendaciones if r['alert_level'] == 'red']
    precaucion = [r for r in recomendaciones if r['alert_level'] == 'yellow']
    ok         = [r for r in recomendaciones if r['alert_level'] == 'green']
    return render(request, 'inventario/dashboard.html', {
        'urgentes': urgentes, 'precaucion': precaucion,
        'ok': ok, 'total': len(recomendaciones),
    })

@login_required
def products_list(request):
    q        = request.GET.get('q', '')
    category = request.GET.get('category', '')
    estado   = request.GET.get('estado', '')
    products = Product.objects.filter(user=request.user, is_active=True)
    if q:
        products = products.filter(name__icontains=q)
    if category:
        products = products.filter(category=category)
    if estado == 'urgente':
        products = products.filter(current_stock__lte=0)
    elif estado == 'precaucion':
        products = products.filter(current_stock__gt=0, current_stock__lte=models.F('safety_stock'))
    elif estado == 'ok':
        products = products.filter(current_stock__gt=models.F('safety_stock'))
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
        'products': products, 'form': form,
        'q': q, 'category': category, 'estado': estado,
    })

@login_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk, user=request.user)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f'✅ Producto "{product.name}" actualizado.')
            return redirect('products_list')
        else:
            messages.error(request, '⚠️ Revisa los campos.')
    else:
        form = ProductForm(instance=product)
    return render(request, 'inventario/product_edit.html', {'form': form, 'product': product})

@login_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk, user=request.user)
    if request.method == 'POST':
        product.is_active = False
        product.save()
        messages.success(request, f'🗑 Producto "{product.name}" eliminado.')
        return redirect('products_list')
    return render(request, 'inventario/product_confirm_delete.html', {'product': product})

@login_required
def ventas(request):
    products = Product.objects.filter(user=request.user, is_active=True)
    today = timezone.now().date()
    ventas_hoy = Sale.objects.filter(
        product__user=request.user,
        sale_date=today
    ).order_by('-created_at')
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        quantity   = request.POST.get('quantity')
        sale_date  = request.POST.get('sale_date')
        notes      = request.POST.get('notes', '')
        if not product_id:
            messages.error(request, '⚠️ Debes seleccionar un producto.')
        elif not sale_date:
            messages.error(request, '⚠️ Debes ingresar una fecha.')
        elif not quantity or int(quantity) < 1:
            messages.error(request, '⚠️ La cantidad debe ser mínimo 1.')
        else:
            product = get_object_or_404(Product, pk=product_id, user=request.user)
            Sale.objects.create(
                product=product,
                quantity_sold=int(quantity),
                sale_date=sale_date,
                notes=notes,
            )
            messages.success(request, f'✅ Venta de {quantity} {product.unit} de "{product.name}" registrada.')
            return redirect('ventas')
    return render(request, 'inventario/ventas.html', {
        'products': products,
        'ventas_hoy': ventas_hoy,
        'today': today,
    })

@login_required
def venta_delete(request, pk):
    venta = get_object_or_404(Sale, pk=pk, product__user=request.user)
    if request.method == 'POST':
        venta.delete()
        messages.success(request, '🗑 Venta eliminada correctamente.')
    return redirect('ventas')

@login_required
def historial(request):
    return render(request, 'inventario/historial.html')

@login_required
def mark_ordered(request, pk):
    product = get_object_or_404(Product, pk=pk, user=request.user)
    if request.method == 'POST':
        rec, created = Recommendation.objects.get_or_create(product=product)
        rec.status = 'ordered'
        rec.save()
        messages.success(request, f'✅ Pedido de "{product.name}" marcado como realizado.')
    return redirect('dashboard')