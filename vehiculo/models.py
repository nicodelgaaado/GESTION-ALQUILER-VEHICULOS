from django.db import models


class Categoria(models.Model):
    nombre = models.CharField(max_length=80, unique=True)
    descripcion = models.TextField(blank=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Tarifa(models.Model):
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.CASCADE,
        related_name="tarifas",
    )
    precio_diario = models.DecimalField(max_digits=10, decimal_places=2)
    activa = models.BooleanField(default=True)
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["categoria__nombre", "-activa", "precio_diario"]

    def __str__(self):
        estado = "activa" if self.activa else "inactiva"
        return f"{self.categoria} - {self.precio_diario} ({estado})"


class Vehiculo(models.Model):
    DISPONIBLE = "disponible"
    MANTENIMIENTO = "mantenimiento"
    INACTIVO = "inactivo"

    ESTADOS = [
        (DISPONIBLE, "Disponible"),
        (MANTENIMIENTO, "Mantenimiento"),
        (INACTIVO, "Inactivo"),
    ]

    placa = models.CharField(max_length=12, unique=True)
    marca = models.CharField(max_length=80)
    modelo = models.CharField(max_length=80)
    anio = models.PositiveIntegerField()
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name="vehiculos",
    )
    estado = models.CharField(max_length=20, choices=ESTADOS, default=DISPONIBLE)
    kilometraje = models.PositiveIntegerField(default=0)
    descripcion = models.TextField(blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["marca", "modelo", "placa"]

    def __str__(self):
        return f"{self.placa} - {self.marca} {self.modelo}"

    @property
    def tarifa_activa(self):
        return self.categoria.tarifas.filter(activa=True).order_by("precio_diario").first()
