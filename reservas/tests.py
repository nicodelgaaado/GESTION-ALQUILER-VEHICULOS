import json
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from project.forms import FleetFlowRegistrationForm
from vehiculo.models import Categoria, Tarifa, Vehiculo
from .models import Reserva


class FlujoAlquilerVehiculosTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(
            username="admin",
            password="admin12345",
            email="admin@example.com",
            is_staff=True,
        )
        self.cliente = User.objects.create_user(
            username="cliente",
            password="cliente12345",
            email="cliente@example.com",
        )
        self.categoria = Categoria.objects.create(nombre="SUV", descripcion="Camionetas")
        self.tarifa = Tarifa.objects.create(
            categoria=self.categoria,
            precio_diario=Decimal("150000.00"),
        )
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

    def patch_json(self, url, data):
        return self.client.patch(
            url,
            data=json.dumps(data),
            content_type="application/json",
        )

    def test_roles_registro_y_superuser_quedan_sincronizados(self):
        User = get_user_model()
        superuser = User.objects.create_superuser(
            username="root@example.com",
            email="root@example.com",
            password="RootPass12345!",
        )
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)
        self.assertEqual(superuser.role, User.ROLE_ADMIN)

        form = FleetFlowRegistrationForm(
            data={
                "full_name": "Admin Demo",
                "company": "FleetFlow",
                "username": "demo-admin@example.com",
                "role": "admin",
                "password1": "AdminPass12345!",
                "password2": "AdminPass12345!",
                "terms": "on",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        registered = form.save()
        self.assertEqual(registered.role, User.ROLE_ADMIN)
        self.assertTrue(registered.is_staff)
        self.assertEqual(registered.empresa, "FleetFlow")

    def test_rutas_api_y_mvt_no_quedan_bajo_api_duplicado(self):
        self.assertEqual(reverse("api_reservas"), "/api/reservas/")
        self.assertEqual(reverse("api_grafico_top_vehiculos"), "/api/graficos/top-vehiculos/")
        self.assertEqual(reverse("api_reservas_reporte_pdf"), "/api/reservas/reporte.pdf")
        self.assertEqual(reverse("vehiculo_list"), "/admin/vehiculos/")
        self.assertEqual(reverse("tarifa_list"), "/admin/tarifas/")
        self.assertEqual(reverse("reserva_create_admin"), "/admin/reservas/crear/")
        self.assertEqual(reverse("mis_reservas"), "/mis-reservas/")
        self.assertEqual(self.client.get("/api/api/reservas/").status_code, 404)

    def test_staff_crea_actualiza_y_elimina_catalogo_por_api(self):
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
        tarifa_id = tarifa_response.json()["id"]

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
        vehiculo_id = vehiculo_response.json()["id"]
        self.assertEqual(vehiculo_response.json()["tarifa_activa"]["precio_diario"], "90000.00")

        update_response = self.patch_json(
            reverse("api_vehiculo_detalle", args=[vehiculo_id]),
            {"kilometraje": 750},
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["kilometraje"], 750)

        self.assertEqual(self.client.delete(reverse("api_vehiculo_detalle", args=[vehiculo_id])).status_code, 204)
        self.assertEqual(self.client.delete(reverse("api_tarifa_detalle", args=[tarifa_id])).status_code, 204)
        self.assertEqual(self.client.delete(reverse("api_categoria_detalle", args=[categoria_id])).status_code, 204)

    def test_reserva_calcula_total_valida_fechas_y_bloquea_solapamiento(self):
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
        self.assertEqual(data["estado"], Reserva.PENDIENTE)
        self.assertEqual(data["total"], "450000.00")

        invalida = self.post_json(
            reverse("api_reservas"),
            {
                "vehiculo_id": self.vehiculo.id,
                "fecha_inicio": "2026-06-04",
                "fecha_fin": "2026-06-04",
            },
        )
        self.assertEqual(invalida.status_code, 400)

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

    def test_check_in_check_out_contrato_y_reporte_pdf(self):
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

        reporte = self.client.get(reverse("api_reservas_reporte_pdf"), {"estado": Reserva.DEVUELTA})
        self.assertEqual(reporte.status_code, 200)
        self.assertEqual(reporte["Content-Type"], "application/pdf")

    def test_admin_crud_reserva_mvt_y_eliminacion_cancela(self):
        self.client.login(username="admin", password="admin12345")

        create_response = self.client.post(
            reverse("reserva_create_admin"),
            {
                "usuario": self.cliente.id,
                "vehiculo": self.vehiculo.id,
                "fecha_inicio": "2026-09-01",
                "fecha_fin": "2026-09-04",
                "estado": Reserva.PENDIENTE,
            },
        )
        self.assertEqual(create_response.status_code, 302)
        reserva = Reserva.objects.get(fecha_inicio=date(2026, 9, 1))
        self.assertEqual(reserva.usuario, self.cliente)
        self.assertEqual(reserva.total, Decimal("450000.00"))

        self.assertEqual(self.client.get(reverse("reserva_detail_admin", args=[reserva.id])).status_code, 200)

        update_response = self.client.post(
            reverse("reserva_update_admin", args=[reserva.id]),
            {
                "usuario": self.cliente.id,
                "vehiculo": self.vehiculo.id,
                "fecha_inicio": "2026-09-01",
                "fecha_fin": "2026-09-05",
                "estado": Reserva.CONFIRMADA,
            },
        )
        self.assertEqual(update_response.status_code, 302)
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, Reserva.CONFIRMADA)
        self.assertEqual(reserva.dias, 4)
        self.assertEqual(reserva.total, Decimal("600000.00"))

        delete_response = self.client.post(reverse("reserva_delete_admin", args=[reserva.id]))
        self.assertEqual(delete_response.status_code, 302)
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, Reserva.CANCELADA)
        self.assertTrue(Reserva.objects.filter(pk=reserva.pk).exists())

    def test_mvt_controla_acceso_por_rol(self):
        self.assertEqual(self.client.get(reverse("vehiculo_list")).status_code, 302)

        self.client.login(username="cliente", password="cliente12345")
        self.assertEqual(self.client.get(reverse("vehiculo_list")).status_code, 302)
        self.assertEqual(self.client.get(reverse("mis_reservas")).status_code, 200)
        self.assertEqual(self.client.get(reverse("reserva_create")).status_code, 200)

        self.client.logout()
        self.client.login(username="admin", password="admin12345")
        for name in ["vehiculo_list", "categoria_list", "tarifa_list", "reserva_list_admin", "reserva_create_admin", "dashboard_admin"]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)

    def test_graficos_devuelven_json_chartjs_desde_datos_reales(self):
        self.client.login(username="cliente", password="cliente12345")
        empty_top = self.client.get(reverse("api_grafico_top_vehiculos"))
        self.assertEqual(empty_top.status_code, 200)
        self.assertEqual(empty_top.json()["labels"], [])
        self.client.logout()

        Reserva.objects.create(
            usuario=self.cliente,
            vehiculo=self.vehiculo,
            fecha_inicio=date(2026, 8, 1),
            fecha_fin=date(2026, 8, 5),
            estado=Reserva.DEVUELTA,
            tarifa_diaria=self.tarifa.precio_diario,
            total=0,
        )
        self.client.login(username="cliente", password="cliente12345")

        for name in [
            "api_grafico_top_vehiculos",
            "api_grafico_ingresos_mensuales",
            "api_grafico_estado_reservas",
        ]:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200, name)
            payload = response.json()
            self.assertIn("labels", payload)
            self.assertIn("datasets", payload)
            self.assertGreaterEqual(len(payload["datasets"]), 1)

    def test_catalogo_sin_vehiculos_no_muestra_datos_inventados(self):
        Vehiculo.objects.all().delete()
        self.client.login(username="cliente", password="cliente12345")
        response = self.client.get(reverse("catalogo"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("No hay vehiculos registrados", content)
        self.assertNotIn("Tesla Model Y", content)
        self.assertNotIn("BMW X5", content)

    def test_busquedas_filtran_catalogo_y_contratos_por_datos_reales(self):
        Reserva.objects.create(
            usuario=self.cliente,
            vehiculo=self.vehiculo,
            fecha_inicio=date(2026, 10, 1),
            fecha_fin=date(2026, 10, 4),
            tarifa_diaria=self.tarifa.precio_diario,
            total=0,
        )

        self.client.login(username="cliente", password="cliente12345")
        catalogo = self.client.get(reverse("catalogo"), {"search": "RAV4"})
        self.assertContains(catalogo, "Toyota RAV4")
        catalogo_sin_resultados = self.client.get(reverse("catalogo"), {"search": "NoExiste"})
        self.assertContains(catalogo_sin_resultados, "No hay vehiculos registrados")

        contratos = self.client.get(reverse("contratos"), {"search": "ABC123"})
        self.assertContains(contratos, "Toyota RAV4")
        contratos_sin_resultados = self.client.get(reverse("contratos"), {"search": "ZZZ999"})
        self.assertContains(contratos_sin_resultados, "Todavia no hay reservas")

        self.client.logout()
        self.client.login(username="admin", password="admin12345")
        admin_reservas = self.client.get(reverse("reserva_list_admin"), {"search": "ABC123"})
        self.assertContains(admin_reservas, "ABC123")

    def test_seed_initial_data_crea_catalogo_sin_reservas_operativas(self):
        call_command("seed_initial_data", verbosity=0)
        User = get_user_model()
        admin = User.objects.get(username="admin@fleetflow.com")
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertEqual(admin.role, User.ROLE_ADMIN)
        self.assertTrue(admin.check_password("admin"))
        self.assertTrue(Vehiculo.objects.filter(placa="EVR241").exists())
        self.assertEqual(Reserva.objects.count(), 0)
        self.assertEqual(
            Vehiculo.objects.filter(
                placa__in=["EVR241", "LUX882", "SUV317", "VAN554", "CTY104", "WRK771"],
                estado=Vehiculo.DISPONIBLE,
            ).count(),
            6,
        )
