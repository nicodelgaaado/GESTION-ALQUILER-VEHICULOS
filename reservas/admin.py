from django.contrib import admin
from .models import Reserva


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ["id", "usuario", "vehiculo", "fecha_inicio", "fecha_fin", "estado", "total"]
    list_filter = ["estado", "fecha_inicio", "fecha_fin"]
    search_fields = ["vehiculo__placa", "usuario__username", "usuario__email"]
