from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
from django.utils import timezone
from .models import Product, Sale
from .forms import ProductForm
from .calculator import calculate_recommendation
from .models import Product, Sale, Recommendation
from django.http import JsonResponse

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
    from datetime import date, timedelta
    from django.db.models import Sum

    products = Product.objects.filter(user=request.user, is_active=True)
    product_id = request.GET.get('product_id', '')
    periodo    = request.GET.get('periodo', '30')

    selected_product = None
    ventas_tabla     = []
    chart_actual     = []
    chart_anterior   = []
    stats            = {}

    if product_id:
        selected_product = get_object_or_404(Product, pk=product_id, user=request.user)
        today     = date.today()
        days      = int(periodo)
        start     = today - timedelta(days=days)
        mid       = today - timedelta(days=days // 2)
        prev_start= start - timedelta(days=days)

        # Tabla de ventas
        ventas_tabla = Sale.objects.filter(
            product=selected_product,
            sale_date__gte=start,
        ).order_by('-sale_date')

        # Stats
        total = ventas_tabla.aggregate(t=Sum('quantity_sold'))['t'] or 0
        avg   = round(total / days, 2)

        recientes  = Sale.objects.filter(product=selected_product, sale_date__gt=mid, sale_date__lte=today).aggregate(t=Sum('quantity_sold'))['t'] or 0
        anteriores = Sale.objects.filter(product=selected_product, sale_date__gte=start, sale_date__lte=mid).aggregate(t=Sum('quantity_sold'))['t'] or 0
        tendencia  = round(((recientes - anteriores) / max(anteriores, 1)) * 100, 1)

        stats = {
            'total':      total,
            'avg':        avg,
            'tendencia':  tendencia,
            'recientes':  recientes,
        }

        # Datos para gráfica — semanas
        semanas_actual   = []
        semanas_anterior = []
        num_semanas = days // 7

        for i in range(num_semanas):
            s = today - timedelta(days=(i + 1) * 7)
            e = today - timedelta(days=i * 7)
            v = Sale.objects.filter(product=selected_product, sale_date__gt=s, sale_date__lte=e).aggregate(t=Sum('quantity_sold'))['t'] or 0
            semanas_actual.insert(0, v)

            sp = s - timedelta(days=days)
            ep = e - timedelta(days=days)
            vp = Sale.objects.filter(product=selected_product, sale_date__gt=sp, sale_date__lte=ep).aggregate(t=Sum('quantity_sold'))['t'] or 0
            semanas_anterior.insert(0, vp)

        chart_actual   = semanas_actual
        chart_anterior = semanas_anterior

    return render(request, 'inventario/historial.html', {
        'products':         products,
        'selected_product': selected_product,
        'product_id':       product_id,
        'periodo':          periodo,
        'ventas_tabla':     ventas_tabla,
        'stats':            stats,
        'chart_actual':     chart_actual,
        'chart_anterior':   chart_anterior,
    })

@login_required
def mark_ordered(request, pk):
    product = get_object_or_404(Product, pk=pk, user=request.user)
    if request.method == 'POST':
        rec, created = Recommendation.objects.get_or_create(product=product)
        rec.status = 'ordered'
        rec.save()
        messages.success(request, f'✅ Pedido de "{product.name}" marcado como realizado.')
    return redirect('dashboard')

@login_required
def recommendation_detail(request, pk):
    product = get_object_or_404(Product, pk=pk, user=request.user)
    r = calculate_recommendation(product)
    return JsonResponse({
        'name':              r['product'].name,
        'unit':              r['product'].unit,
        'current_stock':     r['product'].current_stock,
        'safety_stock':      r['product'].safety_stock,
        'lead_time_days':    r['product'].lead_time_days,
        'avg_daily':         r['avg_daily'],
        'total_30':          r['total_30'],
        'trend_factor':      r['trend_factor'],
        'trend_label':       r['trend_label'],
        'ventas_recientes':  r['ventas_recientes'],
        'ventas_anteriores': r['ventas_anteriores'],
        'projected':         r['projected'],
        'to_order':          r['to_order'],
        'days_remaining':    r['days_remaining'],
        'alert_label':       r['alert_label'],
    })