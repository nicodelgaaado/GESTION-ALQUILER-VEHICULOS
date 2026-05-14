import json
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from vehiculo.models import Categoria, Tarifa, Vehiculo
from .models import Reserva


class FlujoAlquilerVehiculosTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(
            username="admin",
            password="admin12345",
            is_staff=True,
        )
        self.cliente = User.objects.create_user(
            username="cliente",
            password="cliente12345",
            email="cliente@example.com",
        )
        self.categoria = Categoria.objects.create(nombre="SUV", descripcion="Camionetas")
        self.tarifa = Tarifa.objects.create(categoria=self.categoria, precio_diario=Decimal("150000.00"))
        self.vehiculo = Vehiculo.objects.create(
            placa="ABC123",
            marca="Toyota",
            modelo="RAV4",
            anio=2024,
            categoria=self.categoria,
            kilometraje=1000,
        )

    def post_json(self, url, data):
        return self.client.post(
            url,
            data=json.dumps(data),
            content_type="application/json",
        )

    def test_staff_crea_catalogo_por_api(self):
        self.client.login(username="admin", password="admin12345")

        categoria_response = self.post_json(
            reverse("api_categorias"),
            {"nombre": "Compacto", "descripcion": "Autos pequenos"},
        )
        self.assertEqual(categoria_response.status_code, 201)
        categoria_id = categoria_response.json()["id"]

        tarifa_response = self.post_json(
            reverse("api_tarifas"),
            {"categoria_id": categoria_id, "precio_diario": "90000.00", "activa": True},
        )
        self.assertEqual(tarifa_response.status_code, 201)

        vehiculo_response = self.post_json(
            reverse("api_vehiculos"),
            {
                "placa": "XYZ789",
                "marca": "Kia",
                "modelo": "Rio",
                "anio": 2023,
                "categoria_id": categoria_id,
                "kilometraje": 500,
            },
        )
        self.assertEqual(vehiculo_response.status_code, 201)
        self.assertEqual(vehiculo_response.json()["tarifa_activa"]["precio_diario"], "90000.00")

    def test_reserva_calcula_total_y_bloquea_solapamiento(self):
        self.client.login(username="cliente", password="cliente12345")

        response = self.post_json(
            reverse("api_reservas"),
            {
                "vehiculo_id": self.vehiculo.id,
                "fecha_inicio": "2026-06-01",
                "fecha_fin": "2026-06-04",
            },
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["dias"], 3)
        self.assertEqual(data["total"], "450000.00")

        disponibilidad = self.client.get(
            reverse("api_vehiculo_disponibilidad", args=[self.vehiculo.id]),
            {"fecha_inicio": "2026-06-02", "fecha_fin": "2026-06-03"},
        )
        self.assertEqual(disponibilidad.status_code, 200)
        self.assertFalse(disponibilidad.json()["disponible"])

        solapada = self.post_json(
            reverse("api_reservas"),
            {
                "vehiculo_id": self.vehiculo.id,
                "fecha_inicio": "2026-06-02",
                "fecha_fin": "2026-06-05",
            },
        )
        self.assertEqual(solapada.status_code, 400)

    def test_check_in_check_out_y_contrato_pdf(self):
        reserva = Reserva.objects.create(
            usuario=self.cliente,
            vehiculo=self.vehiculo,
            fecha_inicio=date(2026, 7, 1),
            fecha_fin=date(2026, 7, 3),
            tarifa_diaria=self.tarifa.precio_diario,
            total=0,
        )
        self.client.login(username="admin", password="admin12345")

        check_in = self.post_json(
            reverse("api_reserva_check_in", args=[reserva.id]),
            {"kilometraje_salida": 1200},
        )
        self.assertEqual(check_in.status_code, 200)
        self.assertEqual(check_in.json()["estado"], Reserva.EN_ALQUILER)

        check_out = self.post_json(
            reverse("api_reserva_check_out", args=[reserva.id]),
            {"kilometraje_retorno": 1350},
        )
        self.assertEqual(check_out.status_code, 200)
        self.assertEqual(check_out.json()["estado"], Reserva.DEVUELTA)

        contrato = self.client.get(reverse("api_reserva_contrato_pdf", args=[reserva.id]))
        self.assertEqual(contrato.status_code, 200)
        self.assertEqual(contrato["Content-Type"], "application/pdf")
