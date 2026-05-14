from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from vehiculo.models import Tarifa, Vehiculo


class Reserva(models.Model):
    PENDIENTE = "pendiente"
    CONFIRMADA = "confirmada"
    EN_ALQUILER = "en_alquiler"
    DEVUELTA = "devuelta"
    CANCELADA = "cancelada"

    ESTADOS = [
        (PENDIENTE, "Pendiente"),
        (CONFIRMADA, "Confirmada"),
        (EN_ALQUILER, "En alquiler"),
        (DEVUELTA, "Devuelta"),
        (CANCELADA, "Cancelada"),
    ]

    ESTADOS_ACTIVOS = [PENDIENTE, CONFIRMADA, EN_ALQUILER]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reservas",
    )
    vehiculo = models.ForeignKey(
        Vehiculo,
        on_delete=models.PROTECT,
        related_name="reservas",
    )
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default=CONFIRMADA)
    tarifa_diaria = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)
    kilometraje_salida = models.PositiveIntegerField(null=True, blank=True)
    kilometraje_retorno = models.PositiveIntegerField(null=True, blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_inicio", "-creado"]

    def __str__(self):
        return f"Reserva {self.pk or 'nueva'} - {self.vehiculo}"

    @property
    def dias(self):
        return max((self.fecha_fin - self.fecha_inicio).days, 1)

    @classmethod
    def reservas_solapadas(cls, vehiculo, fecha_inicio, fecha_fin):
        return cls.objects.filter(
            vehiculo=vehiculo,
            estado__in=cls.ESTADOS_ACTIVOS,
            fecha_inicio__lt=fecha_fin,
            fecha_fin__gt=fecha_inicio,
        )

    @classmethod
    def vehiculo_disponible(cls, vehiculo, fecha_inicio, fecha_fin, excluir_reserva=None):
        reservas = cls.reservas_solapadas(vehiculo, fecha_inicio, fecha_fin)
        if excluir_reserva:
            reservas = reservas.exclude(pk=excluir_reserva)
        return not reservas.exists()

    def calcular_total(self):
        return self.tarifa_diaria * self.dias

    def clean(self):
        errores = {}
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin <= self.fecha_inicio:
            errores["fecha_fin"] = "La fecha de fin debe ser posterior a la fecha de inicio."

        if self.vehiculo_id and self.fecha_inicio and self.fecha_fin:
            disponible = self.vehiculo_disponible(
                self.vehiculo,
                self.fecha_inicio,
                self.fecha_fin,
                excluir_reserva=self.pk,
            )
            if not disponible:
                errores["vehiculo"] = "El vehiculo no esta disponible para las fechas solicitadas."

        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        if not self.tarifa_diaria and self.vehiculo_id:
            tarifa = Tarifa.objects.filter(
                categoria=self.vehiculo.categoria,
                activa=True,
            ).order_by("precio_diario").first()
            if tarifa:
                self.tarifa_diaria = tarifa.precio_diario
        if self.tarifa_diaria and self.fecha_inicio and self.fecha_fin:
            self.total = self.calcular_total()
        self.full_clean()
        super().save(*args, **kwargs)

    def registrar_check_in(self, kilometraje_salida=None):
        if self.estado not in [self.PENDIENTE, self.CONFIRMADA]:
            raise ValidationError("Solo las reservas pendientes o confirmadas pueden iniciar alquiler.")
        self.estado = self.EN_ALQUILER
        self.check_in = timezone.now()
        if kilometraje_salida is not None:
            self.kilometraje_salida = kilometraje_salida
            self.vehiculo.kilometraje = kilometraje_salida
            self.vehiculo.save(update_fields=["kilometraje", "actualizado"])
        self.save()

    def registrar_check_out(self, kilometraje_retorno=None):
        if self.estado != self.EN_ALQUILER:
            raise ValidationError("Solo las reservas en alquiler pueden registrar devolucion.")
        self.estado = self.DEVUELTA
        self.check_out = timezone.now()
        if kilometraje_retorno is not None:
            self.kilometraje_retorno = kilometraje_retorno
            self.vehiculo.kilometraje = kilometraje_retorno
            self.vehiculo.save(update_fields=["kilometraje", "actualizado"])
        self.save()
