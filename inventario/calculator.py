from datetime import date, timedelta
from django.db.models import Sum
from .models import Sale

def calculate_recommendation(product):
    today = date.today()
    
    # ── Período de 30 días ──────────────────────────────
    start_30 = today - timedelta(days=30)
    total_30 = Sale.objects.filter(
        product=product,
        sale_date__gte=start_30,
        sale_date__lte=today,
    ).aggregate(total=Sum('quantity_sold'))['total'] or 0

    # ── Promedio diario ─────────────────────────────────
    avg_daily = round(total_30 / 30, 2)
    if avg_daily == 0:
        avg_daily = 0.1  # evitar división por cero

    # ── Factor de tendencia ─────────────────────────────
    mid = today - timedelta(days=15)
    start_15 = today - timedelta(days=15)

    ventas_recientes = Sale.objects.filter(
        product=product,
        sale_date__gt=mid,
        sale_date__lte=today,
    ).aggregate(total=Sum('quantity_sold'))['total'] or 0

    ventas_anteriores = Sale.objects.filter(
        product=product,
        sale_date__gte=start_30,
        sale_date__lte=mid,
    ).aggregate(total=Sum('quantity_sold'))['total'] or 0

    if ventas_anteriores > 0:
        trend_factor = round(ventas_recientes / ventas_anteriores, 2)
    else:
        trend_factor = 1.0

    # ── Clasificación de tendencia ──────────────────────
    if trend_factor > 1.2:
        trend_dir = 'up'
        trend_label = '↑ Sube'
    elif trend_factor < 0.8:
        trend_dir = 'down'
        trend_label = '↓ Baja'
    else:
        trend_dir = 'stable'
        trend_label = '→ Estable'

    # ── Proyección y cantidad a pedir ───────────────────
    projected = avg_daily * trend_factor * product.lead_time_days
    to_order = projected + product.safety_stock - product.current_stock
    to_order = max(0, round(to_order))

    # ── Días de stock restantes ─────────────────────────
    days_remaining = round(product.current_stock / avg_daily)

    # ── Nivel de alerta ─────────────────────────────────
    if days_remaining <= product.lead_time_days:
        alert_level = 'red'
        alert_label = '🚨 Urgente'
    elif days_remaining <= product.lead_time_days * 1.5:
        alert_level = 'yellow'
        alert_label = '⚠️ Precaución'
    else:
        alert_level = 'green'
        alert_label = '✅ OK'

    return {
        'product':        product,
        'avg_daily':      avg_daily,
        'total_30':       total_30,
        'trend_factor':   trend_factor,
        'trend_dir':      trend_dir,
        'trend_label':    trend_label,
        'ventas_recientes':  ventas_recientes,
        'ventas_anteriores': ventas_anteriores,
        'projected':      round(projected, 2),
        'to_order':       to_order,
        'days_remaining': days_remaining,
        'alert_level':    alert_level,
        'alert_label':    alert_label,
    }