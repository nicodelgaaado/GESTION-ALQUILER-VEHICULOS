from urllib.parse import urlencode
import json

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from reservas.models import Reserva
from vehiculo.models import Vehiculo

from .forms import FleetFlowAuthenticationForm, FleetFlowRegistrationForm
from .image_services import vehicle_image_asset


NAV_ITEMS = [
    {"label": "Inicio", "icon": "bi-stars", "url_name": "home"},
    {"label": "Panel", "icon": "bi-grid-1x2-fill", "url_name": "dashboard"},
    {"label": "Catalogo", "icon": "bi-car-front-fill", "url_name": "catalogo"},
    {"label": "Contratos", "icon": "bi-file-earmark-richtext-fill", "url_name": "contratos"},
    {"label": "Acceso", "icon": "bi-box-arrow-in-right", "url_name": "login"},
]


def base_context(request, active_page, show_sidebar=False):
    is_admin = request.user.is_authenticated and request.user.is_staff
    return {
        "active_page": active_page,
        "show_sidebar": show_sidebar,
        "nav_items": NAV_ITEMS,
        "is_admin": is_admin,
        "is_client": request.user.is_authenticated and not is_admin,
        "account_role": "Administrador" if is_admin else "Cliente",
    }


def _vehicle_image(make, model, year=None, category=None, seed=None):
    return vehicle_image_asset(make, model, year, category, seed).get("url")


def build_mock_vehicles():
    return [
        {
            "id": 1001,
            "name": "Tesla Model Y",
            "category": "Electrico",
            "price": 145,
            "status": "available",
            "badge": "Disponible",
            "transmission": "Automatico",
            "seats": 5,
            "range": "533 km",
            "plate": "EVR-241",
            "accent": "purple",
            "image_url": _vehicle_image("Tesla", "Model Y", 2024, "Electrico", "fleetflow-tesla"),
        },
        {
            "id": 1002,
            "name": "BMW X5",
            "category": "SUV",
            "price": 180,
            "status": "rented",
            "badge": "En reserva",
            "transmission": "Automatico",
            "seats": 5,
            "range": "740 km",
            "plate": "LUX-882",
            "accent": "blue",
            "image_url": _vehicle_image("BMW", "X5", 2024, "SUV", "fleetflow-bmw"),
        },
        {
            "id": 1003,
            "name": "Renault Duster",
            "category": "SUV",
            "price": 96,
            "status": "available",
            "badge": "Disponible",
            "transmission": "Manual",
            "seats": 5,
            "range": "640 km",
            "plate": "SUV-317",
            "accent": "cyan",
            "image_url": _vehicle_image("Renault", "Duster", 2023, "SUV", "fleetflow-duster"),
        },
        {
            "id": 1004,
            "name": "Mercedes Sprinter",
            "category": "Comercial",
            "price": 220,
            "status": "available",
            "badge": "Disponible",
            "transmission": "Automatico",
            "seats": 12,
            "range": "810 km",
            "plate": "VAN-554",
            "accent": "purple",
            "image_url": _vehicle_image("Mercedes-Benz", "Sprinter", 2024, "Comercial", "fleetflow-sprinter"),
        },
        {
            "id": 1005,
            "name": "Kia Picanto",
            "category": "Urbano",
            "price": 58,
            "status": "rented",
            "badge": "En reserva",
            "transmission": "Automatico",
            "seats": 4,
            "range": "480 km",
            "plate": "CTY-104",
            "accent": "blue",
            "image_url": _vehicle_image("Kia", "Picanto", 2024, "Urbano", "fleetflow-picanto"),
        },
        {
            "id": 1006,
            "name": "Toyota Hilux",
            "category": "Comercial",
            "price": 165,
            "status": "available",
            "badge": "Disponible",
            "transmission": "Automatico",
            "seats": 5,
            "range": "700 km",
            "plate": "WRK-771",
            "accent": "cyan",
            "image_url": _vehicle_image("Toyota", "Hilux", 2024, "Comercial", "fleetflow-hilux"),
        },
    ]


def reservas_para_usuario(user):
    queryset = Reserva.objects.select_related("vehiculo", "vehiculo__categoria", "usuario")
    if user.is_staff:
        return queryset
    return queryset.filter(usuario=user)


def catalogo_backend():
    vehicles = []
    queryset = Vehiculo.objects.select_related("categoria").prefetch_related("categoria__tarifas")
    for vehiculo in queryset:
        tarifa = vehiculo.tarifa_activa
        available = vehiculo.estado == Vehiculo.DISPONIBLE
        vehicles.append(
            {
                "id": vehiculo.id,
                "name": f"{vehiculo.marca} {vehiculo.modelo}",
                "category": vehiculo.categoria.nombre,
                "price": int(tarifa.precio_diario) if tarifa else 0,
                "status": "available" if available else "rented",
                "badge": "Disponible" if available else vehiculo.get_estado_display(),
                "transmission": "Automatico",
                "seats": 5,
                "range": f"{vehiculo.kilometraje} km",
                "plate": vehiculo.placa,
                "accent": "purple" if available else "blue",
                "image_url": _vehicle_image(
                    vehiculo.marca,
                    vehiculo.modelo,
                    vehiculo.anio,
                    vehiculo.categoria.nombre,
                    vehiculo.placa,
                ),
            }
        )
    total = len(vehicles)
    available_count = sum(1 for vehicle in vehicles if vehicle["status"] == "available")
    return {
        "vehicles": vehicles,
        "summary": {
            "total": total,
            "available": available_count,
            "reserved": total - available_count,
            "daily_revenue": sum(
                vehicle["price"] for vehicle in vehicles if vehicle["status"] == "available"
            ),
        },
    }


def dashboard_backend(user):
    reservas_scope = reservas_para_usuario(user)
    reservas = list(reservas_scope.order_by("-creado")[:3])
    vehiculos = list(Vehiculo.objects.all())
    if not reservas and not vehiculos:
        return None

    total_reservas_activas = reservas_scope.filter(
        estado__in=[Reserva.PENDIENTE, Reserva.CONFIRMADA, Reserva.EN_ALQUILER]
    ).count()
    ingresos = sum(float(reserva.total) for reserva in reservas_scope)
    total_vehiculos = len(vehiculos) or 1
    vehiculos_disponibles = sum(1 for vehiculo in vehiculos if vehiculo.estado == Vehiculo.DISPONIBLE)
    devoluciones_vencidas = reservas_scope.filter(estado=Reserva.EN_ALQUILER).count()

    recent_reservations = [
        {
            "client": reserva.usuario.get_full_name() or reserva.usuario.username,
            "vehicle": f"{reserva.vehiculo.marca} {reserva.vehiculo.modelo}",
            "status": reserva.get_estado_display(),
            "total": f"${reserva.total:,.0f}",
        }
        for reserva in reservas
    ]

    return {
        "kpi_cards": [
            {"label": "Alquileres activos", "value": str(total_reservas_activas), "trend": "En vivo"},
            {"label": "Ingresos acumulados", "value": f"${ingresos:,.0f}", "trend": "Base real"},
            {
                "label": "Tasa de utilizacion",
                "value": f"{round(((total_vehiculos - vehiculos_disponibles) / total_vehiculos) * 100)}%",
                "trend": "Base real",
            },
            {"label": "Devoluciones activas", "value": f"{devoluciones_vencidas:02d}", "trend": "Base real"},
        ],
        "recent_reservations": recent_reservations,
    }


def contract_status_tone(reserva):
    if reserva.estado in [Reserva.CONFIRMADA, Reserva.DEVUELTA]:
        return "available"
    if reserva.estado == Reserva.EN_ALQUILER:
        return "processing"
    if reserva.estado == Reserva.CANCELADA:
        return "muted"
    return "rented"


def contract_timeline(reserva):
    sequence = {
        Reserva.PENDIENTE: 1,
        Reserva.CONFIRMADA: 2,
        Reserva.EN_ALQUILER: 3,
        Reserva.DEVUELTA: 4,
        Reserva.CANCELADA: 1,
    }
    active_steps = sequence.get(reserva.estado, 1)
    labels = ["Generado", "Confirmado", "En alquiler", "Completado"]
    return [{"label": label, "active": index < active_steps} for index, label in enumerate(labels)]


def build_contract_mailto(request, reserva):
    contract_code = f"CTR-{reserva.id:05d}"
    pdf_url = request.build_absolute_uri(reverse("api_reserva_contrato_pdf", args=[reserva.id]))
    subject = f"Contrato {contract_code} listo para revision"
    body = (
        f"Hola {reserva.usuario.get_full_name() or reserva.usuario.username},\n\n"
        f"Te compartimos el contrato {contract_code} de tu reserva del vehiculo "
        f"{reserva.vehiculo.marca} {reserva.vehiculo.modelo}.\n"
        f"Descarga el PDF aqui: {pdf_url}\n\nEquipo FleetFlow"
    )
    return f"mailto:{reserva.usuario.email}?{urlencode({'subject': subject, 'body': body})}"


def build_contract_row(reserva, selected_id=None):
    return {
        "id": reserva.id,
        "code": f"CTR-{reserva.id:05d}",
        "client": reserva.usuario.get_full_name() or reserva.usuario.username,
        "vehicle": f"{reserva.vehiculo.marca} {reserva.vehiculo.modelo}",
        "status": reserva.get_estado_display(),
        "status_class": contract_status_tone(reserva),
        "amount": f"${reserva.total:,.0f}",
        "days": f"{reserva.dias} dias",
        "active": reserva.id == selected_id,
        "url": f"{reverse('contratos')}?reserva={reserva.id}",
    }


def build_selected_contract(request, reserva):
    return {
        "id": reserva.id,
        "code": f"CTR-{reserva.id:05d}",
        "status": reserva.get_estado_display(),
        "status_class": contract_status_tone(reserva),
        "client": reserva.usuario.get_full_name() or reserva.usuario.username,
        "client_email": reserva.usuario.email or "Sin correo registrado",
        "vehicle": f"{reserva.vehiculo.marca} {reserva.vehiculo.modelo}",
        "plate": reserva.vehiculo.placa,
        "period": f"{reserva.fecha_inicio:%d %b} - {reserva.fecha_fin:%d %b}",
        "period_full": f"{reserva.fecha_inicio:%d/%m/%Y} - {reserva.fecha_fin:%d/%m/%Y}",
        "total": f"${reserva.total:,.0f}",
        "daily_rate": f"${reserva.tarifa_diaria:,.0f}",
        "days": reserva.dias,
        "timeline": contract_timeline(reserva),
        "pdf_url": reverse("api_reserva_contrato_pdf", args=[reserva.id]),
        "mailto_url": build_contract_mailto(request, reserva),
        "can_approve": request.user.is_staff and reserva.estado == Reserva.PENDIENTE,
        "can_check_in": request.user.is_staff and reserva.estado in [Reserva.PENDIENTE, Reserva.CONFIRMADA],
        "can_check_out": request.user.is_staff and reserva.estado == Reserva.EN_ALQUILER,
        "can_cancel": (request.user.is_staff or reserva.usuario_id == request.user.id)
        and reserva.estado not in [Reserva.EN_ALQUILER, Reserva.DEVUELTA, Reserva.CANCELADA],
        "status_note": {
            Reserva.PENDIENTE: "Pendiente de aprobacion operativa antes de iniciar el alquiler.",
            Reserva.CONFIRMADA: "Listo para check-in y entrega del vehiculo al cliente.",
            Reserva.EN_ALQUILER: "Vehiculo en uso. El siguiente paso real es registrar el check-out.",
            Reserva.DEVUELTA: "Contrato completado y vehiculo devuelto correctamente.",
            Reserva.CANCELADA: "Contrato cancelado. Se conserva solo como trazabilidad.",
        }.get(reserva.estado, "Contrato operativo."),
    }


def home(request):
    context = base_context(request, "home")
    context["hero_stats"] = [
        {"label": "Utilizacion de flota", "value": "92%", "delta": "+8.4%"},
        {"label": "Ingresos mensuales", "value": "$148K", "delta": "+12.1%"},
        {"label": "Contratos aprobados", "value": "324", "delta": "+19 hoy"},
    ]
    context["features"] = [
        "Reservas y disponibilidad en tiempo real",
        "Contratos digitales con flujo de aprobacion",
        "Panel ejecutivo con KPIs y alertas",
        "Catalogo con filtros listos para operacion",
    ]
    context["pricing"] = [
        {"name": "Inicial", "price": "$49", "featured": False},
        {"name": "Crecimiento", "price": "$129", "featured": True},
        {"name": "Empresarial", "price": "Personalizado", "featured": False},
    ]
    return render(request, "index.html", context)


def login_view(request):
    context = base_context(request, "login")
    context["kpis"] = [
        {"label": "Alquileres activos", "value": "218"},
        {"label": "Crecimiento de ingresos", "value": "+18.2%"},
        {"label": "Salud de flota", "value": "96%"},
    ]
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = FleetFlowAuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        messages.success(request, "Sesion iniciada correctamente.")
        return redirect(request.POST.get("next") or request.GET.get("next") or "dashboard")
    context["form"] = form
    return render(request, "login.html", context)


def register_view(request):
    context = base_context(request, "register")
    context["benefits"] = [
        "Elige acceso de cliente o administracion desde el registro",
        "Centraliza contratos y trazabilidad del cliente",
        "Visualiza rentabilidad por categoria en segundos",
    ]
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = FleetFlowRegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Cuenta creada correctamente. Bienvenido a FleetFlow.")
        return redirect("dashboard")
    context["form"] = form
    return render(request, "register.html", context)


@login_required(login_url="login")
def catalogo(request):
    context = base_context(request, "catalogo", show_sidebar=True)
    backend_data = catalogo_backend()
    if backend_data["vehicles"]:
        context["vehicles"] = backend_data["vehicles"]
        context["catalog_summary"] = backend_data["summary"]
    else:
        fallback = build_mock_vehicles()
        context["vehicles"] = fallback
        context["catalog_summary"] = {
            "total": len(fallback),
            "available": sum(1 for vehicle in fallback if vehicle["status"] == "available"),
            "reserved": sum(1 for vehicle in fallback if vehicle["status"] != "available"),
            "daily_revenue": sum(
                vehicle["price"] for vehicle in fallback if vehicle["status"] == "available"
            ),
        }
    return render(request, "catalogo.html", context)


@login_required(login_url="login")
def dashboard(request):
    context = base_context(request, "dashboard", show_sidebar=True)
    backend_data = dashboard_backend(request.user)
    if backend_data:
        context.update(backend_data)
    else:
        context["kpi_cards"] = [
            {"label": "Alquileres activos", "value": "218", "trend": "+12%"},
            {"label": "Ingresos mensuales", "value": "$148K", "trend": "+9%"},
            {"label": "Tasa de utilizacion", "value": "92%", "trend": "+3%"},
            {"label": "Devoluciones vencidas", "value": "07", "trend": "-2%"},
        ]
        context["recent_reservations"] = [
            {"client": "Juan Rivera", "vehicle": "Tesla Model Y", "status": "Confirmada", "total": "$580"},
            {"client": "Logistica Nova", "vehicle": "Mercedes Sprinter", "status": "En curso", "total": "$1,920"},
            {"client": "Camila Perez", "vehicle": "Kia Picanto", "status": "Pendiente", "total": "$174"},
        ]
    return render(request, "dashboard.html", context)


@login_required(login_url="login")
def contratos(request):
    context = base_context(request, "contratos", show_sidebar=True)
    queryset = reservas_para_usuario(request.user).order_by("-creado")

    selected = None
    selected_id = request.GET.get("reserva")
    if selected_id and selected_id.isdigit():
        selected = queryset.filter(pk=int(selected_id)).first()

    vehicle_id = request.GET.get("vehiculo")
    if not selected and vehicle_id and vehicle_id.isdigit():
        selected = queryset.filter(vehiculo_id=int(vehicle_id)).first()

    if request.method == "POST":
        selected = get_object_or_404(queryset, pk=request.POST.get("reserva_id"))
        action = request.POST.get("action")
        if action == "approve" and request.user.is_staff and selected.estado == Reserva.PENDIENTE:
            selected.estado = Reserva.CONFIRMADA
            selected.save(update_fields=["estado", "actualizado"])
            messages.success(request, f"{selected.vehiculo} aprobado para el cliente.")
        elif action == "check_in" and request.user.is_staff:
            selected.registrar_check_in(selected.vehiculo.kilometraje)
            messages.success(request, "Check-in registrado correctamente.")
        elif action == "check_out" and request.user.is_staff:
            selected.registrar_check_out(selected.vehiculo.kilometraje)
            messages.success(request, "Check-out registrado correctamente.")
        elif action == "cancel" and (
            request.user.is_staff or selected.usuario_id == request.user.id
        ) and selected.estado not in [Reserva.EN_ALQUILER, Reserva.DEVUELTA, Reserva.CANCELADA]:
            selected.estado = Reserva.CANCELADA
            selected.save(update_fields=["estado", "actualizado"])
            messages.info(request, "La reserva se cancelo y quedo registrada en el historial.")
        else:
            messages.warning(request, "La accion solicitada no esta disponible para este contrato.")
        return redirect(f"{reverse('contratos')}?{urlencode({'reserva': selected.id})}")

    selected = selected or queryset.first()
    context["contracts"] = [build_contract_row(reserva, selected.id if selected else None) for reserva in queryset[:12]]
    context["selected_contract"] = build_selected_contract(request, selected) if selected else None
    return render(request, "contratos.html", context)


def logout_view(request):
    logout(request)
    messages.info(request, "Sesion cerrada.")
    return redirect("login")


def hero_vehicle_image(request):
    """Devuelve una imagen de vehículo para la sección hero"""
    try:
        # Buscar en orden: Tesla primero, luego fallback a otro auto
        image_asset = vehicle_image_asset("Tesla", "Model 3", 2024, "Electrico", "fleetflow-tesla-hero")
        return JsonResponse({"url": image_asset.get("url"), "source": image_asset.get("source")})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def fleet_stats(request):
    """Devuelve estadísticas en tiempo real de la flota"""
    try:
        vehicles = Vehiculo.objects.select_related("categoria").prefetch_related("categoria__tarifas")
        reservas = Reserva.objects.filter(estado__in=[Reserva.PENDIENTE, Reserva.CONFIRMADA, Reserva.EN_ALQUILER])
        
        total_vehicles = vehicles.count()
        available = sum(1 for v in vehicles if v.estado == Vehiculo.DISPONIBLE)
        rented = total_vehicles - available
        
        total_revenue = sum(float(r.total) for r in Reserva.objects.filter(estado__in=[Reserva.CONFIRMADA, Reserva.DEVUELTA]))
        daily_revenue = sum(float(r.total) for r in reservas) / max(reservas.count(), 1)
        
        # Estadísticas por categoría
        categories = {}
        for vehicle in vehicles:
            cat_name = vehicle.categoria.nombre if vehicle.categoria else "Sin categoría"
            if cat_name not in categories:
                categories[cat_name] = {"total": 0, "available": 0}
            categories[cat_name]["total"] += 1
            if vehicle.estado == Vehiculo.DISPONIBLE:
                categories[cat_name]["available"] += 1
        
        # Generar datos para las barras del gráfico (últimos 7 días simulado)
        chart_data = [
            42, 55, 68, 72, 88, 82, 94  # Porcentajes de utilización
        ]
        
        return JsonResponse({
            "total_vehicles": total_vehicles,
            "available": available,
            "rented": rented,
            "utilization_rate": round((rented / max(total_vehicles, 1)) * 100),
            "daily_revenue": round(daily_revenue, 2),
            "total_revenue": round(total_revenue, 2),
            "active_reservations": reservas.count(),
            "categories": categories,
            "chart_data": chart_data,
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
