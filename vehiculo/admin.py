from django.contrib import admin
from .models import Categoria, Tarifa, Vehiculo


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    search_fields = ["nombre"]


@admin.register(Tarifa)
class TarifaAdmin(admin.ModelAdmin):
    list_display = ["categoria", "precio_diario", "activa"]
    list_filter = ["activa", "categoria"]


@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display = ["placa", "marca", "modelo", "anio", "categoria", "estado", "kilometraje"]
    list_filter = ["estado", "categoria", "marca"]
    search_fields = ["placa", "marca", "modelo"]
