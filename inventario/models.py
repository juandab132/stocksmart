from django.db import models
from django.contrib.auth.models import User

class Product(models.Model):
    CATEGORIAS = [
        ('granos', 'Granos y cereales'),
        ('aceites', 'Aceites'),
        ('aseo', 'Aseo'),
        ('lacteos', 'Lácteos'),
        ('otros', 'Otros'),
    ]
    UNIDADES = [
        ('u', 'Unidades'),
        ('kg', 'Kilogramos'),
        ('l', 'Litros'),
        ('g', 'Gramos'),
    ]
    user          = models.ForeignKey(User, on_delete=models.CASCADE)
    name          = models.CharField(max_length=200)
    category      = models.CharField(max_length=50, choices=CATEGORIAS)
    unit          = models.CharField(max_length=10, choices=UNIDADES)
    current_stock = models.IntegerField(default=0)
    safety_stock  = models.IntegerField(default=0)
    lead_time_days= models.IntegerField(default=1)
    notes         = models.TextField(blank=True)
    is_active     = models.BooleanField(default=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Sale(models.Model):
    product       = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity_sold = models.IntegerField()
    sale_date     = models.DateField()
    notes         = models.TextField(blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product} - {self.quantity_sold} u - {self.sale_date}"