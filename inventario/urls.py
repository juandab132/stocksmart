from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('productos/', views.products_list, name='products_list'),
    path('productos/<int:pk>/editar/', views.product_edit, name='product_edit'),
    path('productos/<int:pk>/eliminar/', views.product_delete, name='product_delete'),
    path('ventas/', views.ventas, name='ventas'),
    path('ventas/<int:pk>/eliminar/', views.venta_delete, name='venta_delete'),
    path('historial/', views.historial, name='historial'),
    path('productos/<int:pk>/pedido/', views.mark_ordered, name='mark_ordered'),
]