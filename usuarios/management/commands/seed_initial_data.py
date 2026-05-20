from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from vehiculo.models import Categoria, Tarifa, Vehiculo


class Command(BaseCommand):
    help = "Crea usuarios y datos iniciales de catalogo sin reservas operativas."

    def handle(self, *args, **options):
        User = get_user_model()
        self._upsert_user(
            User,
            username="admin@fleetflow.com",
            email="admin@fleetflow.com",
            password="admin",
            first_name="Admin",
            last_name="FleetFlow",
            role=User.ROLE_ADMIN,
            is_staff=True,
            is_superuser=True,
            empresa="FleetFlow",
        )
        self._upsert_user(
            User,
            username="cliente@fleetflow.com",
            email="cliente@fleetflow.com",
            password="cliente123",
            first_name="Laura",
            last_name="Mendoza",
            role=User.ROLE_CLIENTE,
            is_staff=False,
            is_superuser=False,
            empresa="Aurora Rentals",
        )

        categorias = {
            "Electrico": "Vehiculos electricos para uso ejecutivo y urbano.",
            "SUV": "Camionetas familiares y corporativas.",
            "Comercial": "Vehiculos de carga y transporte operativo.",
            "Urbano": "Autos compactos para recorridos de ciudad.",
        }
        categoria_objs = {
            nombre: Categoria.objects.update_or_create(
                nombre=nombre,
                defaults={"descripcion": descripcion},
            )[0]
            for nombre, descripcion in categorias.items()
        }

        tarifas = {
            "Electrico": Decimal("145000.00"),
            "SUV": Decimal("180000.00"),
            "Comercial": Decimal("220000.00"),
            "Urbano": Decimal("58000.00"),
        }
        for nombre, precio in tarifas.items():
            Tarifa.objects.update_or_create(
                categoria=categoria_objs[nombre],
                activa=True,
                defaults={"precio_diario": precio},
            )

        vehiculos = [
            ("EVR241", "Tesla", "Model Y", 2024, "Electrico", 18400),
            ("LUX882", "BMW", "X5", 2024, "SUV", 22100),
            ("SUV317", "Renault", "Duster", 2023, "SUV", 31050),
            ("VAN554", "Mercedes", "Sprinter", 2024, "Comercial", 12600),
            ("CTY104", "Kia", "Picanto", 2024, "Urbano", 9800),
            ("WRK771", "Toyota", "Hilux", 2024, "Comercial", 19020),
        ]
        for placa, marca, modelo, anio, categoria, kilometraje in vehiculos:
            Vehiculo.objects.update_or_create(
                placa=placa,
                defaults={
                    "marca": marca,
                    "modelo": modelo,
                    "anio": anio,
                    "categoria": categoria_objs[categoria],
                    "estado": Vehiculo.DISPONIBLE,
                    "kilometraje": kilometraje,
                    "descripcion": "Vehiculo base creado para operar el catalogo inicial.",
                },
            )

        self.stdout.write(self.style.SUCCESS("Datos iniciales listos sin reservas creadas."))
        self.stdout.write("Admin: admin@fleetflow.com / admin")
        self.stdout.write("Cliente: cliente@fleetflow.com / cliente123")

    def _upsert_user(self, User, username, email, password, **defaults):
        user = User.objects.filter(username=username).first() or User.objects.filter(email=email).first()
        if user is None:
            user = User(username=username, email=email)
        user.username = username
        user.email = email
        for field, value in defaults.items():
            setattr(user, field, value)
        user.set_password(password)
        user.save()
        return user
