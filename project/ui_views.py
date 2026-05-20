from datetime import timedelta
from urllib.parse import urlencode
import json

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from reservas.models import Reserva
from vehiculo.models import Categoria, Vehiculo

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


def reservas_para_usuario(user):
    queryset = Reserva.objects.select_related("vehiculo", "vehiculo__categoria", "usuario")
    if user.is_staff:
        return queryset
    return queryset.filter(usuario=user)


def reservas_activas_en_dia(fecha):
    return Reserva.objects.filter(
        estado__in=Reserva.ESTADOS_ACTIVOS,
        fecha_inicio__lt=fecha + timedelta(days=1),
        fecha_fin__gt=fecha,
    )


def ids_vehiculos_ocupados(fecha):
    return set(reservas_activas_en_dia(fecha).values_list("vehiculo_id", flat=True))


def catalogo_backend(search="", category="", availability=""):
    vehicles = []
    hoy = timezone.localdate()
    ocupados_hoy = ids_vehiculos_ocupados(hoy)
    queryset = Vehiculo.objects.select_related("categoria").prefetch_related("categoria__tarifas")
    if search:
        queryset = queryset.filter(
            Q(placa__icontains=search)
            | Q(marca__icontains=search)
            | Q(modelo__icontains=search)
            | Q(categoria__nombre__icontains=search)
        )
    if category and category != "all":
        queryset = queryset.filter(categoria__nombre=category)
    for vehiculo in queryset:
        tarifa = vehiculo.tarifa_activa
        reservado_hoy = vehiculo.id in ocupados_hoy
        available = vehiculo.estado == Vehiculo.DISPONIBLE and not reservado_hoy
        if available:
            status = "available"
            badge = "Disponible"
            accent = "purple"
        elif reservado_hoy:
            status = "rented"
            badge = "Reservado hoy"
            accent = "blue"
        else:
            status = "unavailable"
            badge = vehiculo.get_estado_display()
            accent = "cyan"
        if not availability or availability == "all" or availability == status:
            vehicles.append(
                {
                    "id": vehiculo.id,
                    "name": f"{vehiculo.marca} {vehiculo.modelo}",
                    "category": vehiculo.categoria.nombre,
                    "price": int(tarifa.precio_diario) if tarifa else 0,
                    "status": status,
                    "badge": badge,
                    "transmission": "Automatico",
                    "seats": 5,
                    "range": f"{vehiculo.kilometraje} km",
                    "plate": vehiculo.placa,
                    "accent": accent,
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
    reserved_count = sum(1 for vehicle in vehicles if vehicle["status"] == "rented")
    max_price = max([vehicle["price"] for vehicle in vehicles], default=0)
    return {
        "vehicles": vehicles,
        "summary": {
            "total": total,
            "available": available_count,
            "reserved": reserved_count,
            "unavailable": total - available_count - reserved_count,
            "max_price": max_price,
            "daily_revenue": sum(
                vehicle["price"] for vehicle in vehicles if vehicle["status"] == "available"
            ),
        },
    }


def dashboard_backend(user):
    reservas_scope = reservas_para_usuario(user)
    reservas = list(reservas_scope.order_by("-creado")[:3])
    vehiculos = list(Vehiculo.objects.all())

    total_reservas_activas = reservas_scope.filter(
        estado__in=[Reserva.PENDIENTE, Reserva.CONFIRMADA, Reserva.EN_ALQUILER]
    ).count()
    ingresos = sum(float(reserva.total) for reserva in reservas_scope)
    total_vehiculos = len(vehiculos)
    vehiculos_disponibles = sum(1 for vehiculo in vehiculos if vehiculo.estado == Vehiculo.DISPONIBLE)
    devoluciones_vencidas = reservas_scope.filter(estado=Reserva.EN_ALQUILER).count()
    utilization_rate = round(((total_vehiculos - vehiculos_disponibles) / total_vehiculos) * 100) if total_vehiculos else 0

    hoy = timezone.localdate()
    alertas = []
    pendientes = reservas_scope.filter(estado=Reserva.PENDIENTE).count()
    vencidas = reservas_scope.filter(estado=Reserva.EN_ALQUILER, fecha_fin__lt=hoy).count()
    mantenimiento = Vehiculo.objects.filter(estado=Vehiculo.MANTENIMIENTO).count()
    if pendientes:
        alertas.append(f"{pendientes} reserva{'s' if pendientes != 1 else ''} pendiente{'s' if pendientes != 1 else ''} de aprobacion.")
    if vencidas:
        alertas.append(f"{vencidas} alquiler{'es' if vencidas != 1 else ''} activo{'s' if vencidas != 1 else ''} con fecha de devolucion vencida.")
    if mantenimiento:
        alertas.append(f"{mantenimiento} vehiculo{'s' if mantenimiento != 1 else ''} en mantenimiento.")

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
                "value": f"{utilization_rate}%",
                "trend": "Base real",
            },
            {"label": "Devoluciones activas", "value": f"{devoluciones_vencidas:02d}", "trend": "Base real"},
        ],
        "recent_reservations": recent_reservations,
        "alerts": alertas,
        "alerts_count": len(alertas),
        "revenue_trend_label": "Base real",
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


def build_contract_row(reserva, selected_id=None, search=""):
    params = {"reserva": reserva.id}
    if search:
        params["search"] = search
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
        "url": f"{reverse('contratos')}?{urlencode(params)}",
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


def metricas_operativas():
    hoy = timezone.localdate()
    inicio_mes = hoy.replace(day=1)
    total_vehiculos = Vehiculo.objects.count()
    ocupados_hoy = ids_vehiculos_ocupados(hoy)
    vehiculos_disponibles = Vehiculo.objects.filter(estado=Vehiculo.DISPONIBLE).exclude(
        id__in=ocupados_hoy
    ).count()
    vehiculos_ocupados = len(ocupados_hoy)
    utilizacion = round((vehiculos_ocupados / total_vehiculos) * 100) if total_vehiculos else 0
    ingresos_mes = Reserva.objects.filter(
        estado=Reserva.DEVUELTA,
        actualizado__date__gte=inicio_mes,
    ).aggregate(total=Sum("total"))["total"] or 0
    contratos_aprobados = Reserva.objects.filter(estado=Reserva.CONFIRMADA).count()
    reservas_hoy = reservas_activas_en_dia(hoy).select_related("vehiculo")
    ingreso_diario = sum(float(reserva.total) / reserva.dias for reserva in reservas_hoy)
    barras = []
    for offset in range(6, -1, -1):
        fecha = hoy - timedelta(days=offset)
        ocupacion = reservas_activas_en_dia(fecha).values("vehiculo_id").distinct().count()
        porcentaje = round((ocupacion / total_vehiculos) * 100) if total_vehiculos else 0
        barras.append({
            "label": fecha.strftime("%a"),
            "value": porcentaje,
        })
    return {
        "total_vehiculos": total_vehiculos,
        "vehiculos_disponibles": vehiculos_disponibles,
        "utilizacion": utilizacion,
        "ingresos_mes": ingresos_mes,
        "contratos_aprobados": contratos_aprobados,
        "ingreso_diario": ingreso_diario,
        "barras_ocupacion": barras,
    }


def home(request):
    context = base_context(request, "home")
    metricas = metricas_operativas()
    context["hero_stats"] = [
        {"label": "Utilizacion actual", "value": f"{metricas['utilizacion']}%", "delta": "Base real"},
        {"label": "Ingresos del mes", "value": f"${metricas['ingresos_mes']:,.0f}", "delta": "Reservas devueltas"},
        {"label": "Contratos confirmados", "value": str(metricas["contratos_aprobados"]), "delta": "Base real"},
    ]
    context["hero_panel_metrics"] = [
        {"label": "Ingreso diario", "value": f"${metricas['ingreso_diario']:,.0f}", "accent": "accent-purple"},
        {"label": "Tasa de uso", "value": f"{metricas['utilizacion']}%", "accent": "accent-blue"},
    ]
    context["weekly_occupancy"] = metricas["barras_ocupacion"]
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
    metricas = metricas_operativas()
    pendientes = Reserva.objects.filter(estado=Reserva.PENDIENTE).count()
    context["kpis"] = [
        {"label": "Alquileres activos", "value": str(Reserva.objects.filter(estado__in=Reserva.ESTADOS_ACTIVOS).count())},
        {"label": "Vehiculos disponibles", "value": str(metricas["vehiculos_disponibles"])},
        {"label": "Reservas pendientes", "value": str(pendientes)},
    ]
    context["today_focus"] = (
        f"Hoy hay {pendientes} reserva{'s' if pendientes != 1 else ''} pendiente{'s' if pendientes != 1 else ''} "
        f"y {metricas['vehiculos_disponibles']} vehiculo{'s' if metricas['vehiculos_disponibles'] != 1 else ''} disponible{'s' if metricas['vehiculos_disponibles'] != 1 else ''}."
    )
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
    search = request.GET.get("search", "").strip()
    category = request.GET.get("category", "").strip()
    availability = request.GET.get("availability", "").strip()
    backend_data = catalogo_backend(search=search, category=category, availability=availability)
    context["vehicles"] = backend_data["vehicles"]
    context["catalog_summary"] = backend_data["summary"]
    context["catalog_categories"] = Categoria.objects.values_list("nombre", flat=True)
    context["search"] = search
    context["category_filter"] = category
    context["availability_filter"] = availability
    return render(request, "catalogo.html", context)


@login_required(login_url="login")
def dashboard(request):
    context = base_context(request, "dashboard", show_sidebar=True)
    backend_data = dashboard_backend(request.user)
    context.update(backend_data)
    return render(request, "dashboard.html", context)


@login_required(login_url="login")
def contratos(request):
    context = base_context(request, "contratos", show_sidebar=True)
    queryset = reservas_para_usuario(request.user).order_by("-creado")
    search = request.GET.get("search", "").strip()
    if search:
        search_filter = (
            Q(usuario__username__icontains=search)
            | Q(usuario__email__icontains=search)
            | Q(usuario__first_name__icontains=search)
            | Q(usuario__last_name__icontains=search)
            | Q(vehiculo__placa__icontains=search)
            | Q(vehiculo__marca__icontains=search)
            | Q(vehiculo__modelo__icontains=search)
        )
        normalized = search.upper().replace("CTR-", "").strip()
        if normalized.isdigit():
            search_filter |= Q(pk=int(normalized))
        queryset = queryset.filter(search_filter)
    context["search"] = search

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
        try:
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
        except ValidationError as exc:
            messages.error(request, f"No se pudo ejecutar la accion: {exc}")
        return redirect(f"{reverse('contratos')}?{urlencode({'reserva': selected.id})}")

    selected = selected or queryset.first()
    context["contracts"] = [build_contract_row(reserva, selected.id if selected else None, search) for reserva in queryset[:12]]
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
        hoy = timezone.localdate()
        vehicles = Vehiculo.objects.select_related("categoria").prefetch_related("categoria__tarifas")
        reservas_activas = Reserva.objects.filter(estado__in=Reserva.ESTADOS_ACTIVOS)
        reservas_hoy = reservas_activas_en_dia(hoy)
        ocupados_hoy = set(reservas_hoy.values_list("vehiculo_id", flat=True))
        
        total_vehicles = vehicles.count()
        available = sum(1 for v in vehicles if v.estado == Vehiculo.DISPONIBLE and v.id not in ocupados_hoy)
        rented = len(ocupados_hoy)
        
        total_revenue = sum(float(r.total) for r in Reserva.objects.filter(estado__in=[Reserva.CONFIRMADA, Reserva.DEVUELTA]))
        daily_revenue = sum(float(r.total) / r.dias for r in reservas_hoy)
        
        # Estadísticas por categoría
        categories = {}
        for vehicle in vehicles:
            cat_name = vehicle.categoria.nombre if vehicle.categoria else "Sin categoría"
            if cat_name not in categories:
                categories[cat_name] = {"total": 0, "available": 0}
            categories[cat_name]["total"] += 1
            if vehicle.estado == Vehiculo.DISPONIBLE:
                categories[cat_name]["available"] += 1
        
        chart_data = []
        for offset in range(6, -1, -1):
            fecha = hoy - timedelta(days=offset)
            ocupacion = reservas_activas_en_dia(fecha).values("vehiculo_id").distinct().count()
            chart_data.append(round((ocupacion / total_vehicles) * 100) if total_vehicles else 0)
        
        return JsonResponse({
            "total_vehicles": total_vehicles,
            "available": available,
            "rented": rented,
            "utilization_rate": round((rented / max(total_vehicles, 1)) * 100),
            "daily_revenue": round(daily_revenue, 2),
            "total_revenue": round(total_revenue, 2),
            "active_reservations": reservas_activas.count(),
            "categories": categories,
            "chart_data": chart_data,
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
