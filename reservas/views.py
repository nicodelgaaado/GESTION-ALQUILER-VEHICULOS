from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction
from django.http import FileResponse, JsonResponse
from django.utils.dateparse import parse_date
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from vehiculo.models import Tarifa, Vehiculo
from vehiculo.views import leer_json, respuesta_error, usuario_autenticado
from .models import Reserva


def fecha_desde_payload(payload, campo):
    valor = payload.get(campo)
    fecha = parse_date(valor) if valor else None
    if not fecha:
        raise ValueError(f"El campo {campo} debe tener formato YYYY-MM-DD.")
    return fecha


def reserva_json(reserva):
    return {
        "id": reserva.id,
        "usuario": {
            "id": reserva.usuario.id,
            "username": reserva.usuario.username,
            "email": reserva.usuario.email,
        },
        "vehiculo": {
            "id": reserva.vehiculo.id,
            "placa": reserva.vehiculo.placa,
            "marca": reserva.vehiculo.marca,
            "modelo": reserva.vehiculo.modelo,
            "categoria": reserva.vehiculo.categoria.nombre,
        },
        "fecha_inicio": reserva.fecha_inicio.isoformat(),
        "fecha_fin": reserva.fecha_fin.isoformat(),
        "dias": reserva.dias,
        "estado": reserva.estado,
        "tarifa_diaria": str(reserva.tarifa_diaria),
        "total": str(reserva.total),
        "check_in": reserva.check_in.isoformat() if reserva.check_in else None,
        "check_out": reserva.check_out.isoformat() if reserva.check_out else None,
        "kilometraje_salida": reserva.kilometraje_salida,
        "kilometraje_retorno": reserva.kilometraje_retorno,
    }


def reservas_para_usuario(user):
    queryset = Reserva.objects.select_related("usuario", "vehiculo", "vehiculo__categoria")
    if user.is_staff:
        return queryset
    return queryset.filter(usuario=user)


def obtener_reserva(reserva_id, user):
    return reservas_para_usuario(user).get(pk=reserva_id)


def usuario_reserva(user, payload):
    if user.is_staff and payload.get("usuario_id"):
        return get_user_model().objects.get(pk=payload["usuario_id"])
    return user


def aplicar_reserva(reserva, payload, user):
    if not reserva.pk:
        faltantes = [campo for campo in ["vehiculo_id", "fecha_inicio", "fecha_fin"] if campo not in payload]
        if faltantes:
            raise ValueError(f"Campos obligatorios faltantes: {', '.join(faltantes)}.")
        reserva.usuario = usuario_reserva(user, payload)

    if "vehiculo_id" in payload:
        reserva.vehiculo = Vehiculo.objects.select_related("categoria").get(pk=payload["vehiculo_id"])
    if "fecha_inicio" in payload:
        reserva.fecha_inicio = fecha_desde_payload(payload, "fecha_inicio")
    if "fecha_fin" in payload:
        reserva.fecha_fin = fecha_desde_payload(payload, "fecha_fin")
    if user.is_staff and "estado" in payload:
        reserva.estado = payload["estado"]

    if reserva.vehiculo.estado != Vehiculo.DISPONIBLE:
        raise ValidationError("El vehiculo no esta disponible para reservas.")

    tarifa = Tarifa.objects.filter(
        categoria=reserva.vehiculo.categoria,
        activa=True,
    ).order_by("precio_diario").first()
    if not tarifa:
        raise ValidationError("La categoria del vehiculo no tiene una tarifa activa.")

    reserva.tarifa_diaria = tarifa.precio_diario
    reserva.total = reserva.calcular_total()
    reserva.save()
    return reserva


@csrf_exempt
@require_http_methods(["GET", "POST"])
def reservas(request):
    user = usuario_autenticado(request)
    if not user:
        return respuesta_error("Debe autenticarse para gestionar reservas.", status=401)

    if request.method == "GET":
        data = [reserva_json(reserva) for reserva in reservas_para_usuario(user)]
        return JsonResponse({"resultados": data})

    try:
        with transaction.atomic():
            reserva = aplicar_reserva(Reserva(), leer_json(request), user)
    except (ValueError, ValidationError, ObjectDoesNotExist) as exc:
        return respuesta_error("No se pudo crear la reserva.", errores=str(exc))
    return JsonResponse(reserva_json(reserva), status=201)


@csrf_exempt
@require_http_methods(["GET", "PUT", "PATCH", "DELETE"])
def reserva_detalle(request, reserva_id):
    user = usuario_autenticado(request)
    if not user:
        return respuesta_error("Debe autenticarse para gestionar reservas.", status=401)

    try:
        reserva = obtener_reserva(reserva_id, user)
    except Reserva.DoesNotExist:
        return respuesta_error("Reserva no encontrada.", status=404)

    if request.method == "GET":
        return JsonResponse(reserva_json(reserva))

    if request.method == "DELETE":
        if reserva.estado == Reserva.EN_ALQUILER:
            return respuesta_error("No se puede cancelar una reserva en alquiler.")
        reserva.estado = Reserva.CANCELADA
        reserva.save(update_fields=["estado", "actualizado"])
        return JsonResponse(reserva_json(reserva))

    try:
        with transaction.atomic():
            reserva = aplicar_reserva(reserva, leer_json(request), user)
    except (ValueError, ValidationError, ObjectDoesNotExist) as exc:
        return respuesta_error("No se pudo actualizar la reserva.", errores=str(exc))
    return JsonResponse(reserva_json(reserva))


@csrf_exempt
@require_http_methods(["POST"])
def reserva_check_in(request, reserva_id):
    user = usuario_autenticado(request)
    if not user or not user.is_staff:
        return respuesta_error("Solo administradores pueden registrar check-in.", status=403)

    try:
        payload = leer_json(request)
        reserva = Reserva.objects.select_related("vehiculo", "usuario", "vehiculo__categoria").get(pk=reserva_id)
        reserva.registrar_check_in(payload.get("kilometraje_salida"))
    except (ValueError, ValidationError) as exc:
        return respuesta_error("No se pudo registrar el check-in.", errores=str(exc))
    except Reserva.DoesNotExist:
        return respuesta_error("Reserva no encontrada.", status=404)
    return JsonResponse(reserva_json(reserva))


@csrf_exempt
@require_http_methods(["POST"])
def reserva_check_out(request, reserva_id):
    user = usuario_autenticado(request)
    if not user or not user.is_staff:
        return respuesta_error("Solo administradores pueden registrar check-out.", status=403)

    try:
        payload = leer_json(request)
        reserva = Reserva.objects.select_related("vehiculo", "usuario", "vehiculo__categoria").get(pk=reserva_id)
        reserva.registrar_check_out(payload.get("kilometraje_retorno"))
    except (ValueError, ValidationError) as exc:
        return respuesta_error("No se pudo registrar el check-out.", errores=str(exc))
    except Reserva.DoesNotExist:
        return respuesta_error("Reserva no encontrada.", status=404)
    return JsonResponse(reserva_json(reserva))


@require_http_methods(["GET"])
def reserva_contrato_pdf(request, reserva_id):
    user = usuario_autenticado(request)
    if not user:
        return respuesta_error("Debe autenticarse para descargar el contrato.", status=401)

    try:
        reserva = obtener_reserva(reserva_id, user)
    except Reserva.DoesNotExist:
        return respuesta_error("Reserva no encontrada.", status=404)

    from reportlab.lib.colors import HexColor
    from reportlab.lib.units import inch

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    margin = 72
    y = height - margin

    # Membrete superior
    pdf.setFillColor(HexColor("#1e1b4b"))
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(margin, y, "FLEETFLOW")
    pdf.setFont("Helvetica", 9)
    pdf.setFillColor(HexColor("#64748b"))
    pdf.drawString(margin, y - 14, "Sistema de alquiler vehicular — Contrato digital")
    y -= 40

    # Línea separadora
    pdf.setStrokeColor(HexColor("#cbd5e1"))
    pdf.line(margin, y, width - margin, y)
    y -= 24

    # Título
    pdf.setFillColor(HexColor("#0f172a"))
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(margin, y, "CONTRATO DE ALQUILER DE VEHÍCULO")
    y -= 14
    pdf.setFont("Helvetica", 10)
    pdf.setFillColor(HexColor("#475569"))
    pdf.drawString(margin, y, f"Contrato No. CTR-{reserva.id:05d}  |  {reserva.creado.strftime('%d/%m/%Y')}")
    y -= 36

    # Datos del cliente
    pdf.setFillColor(HexColor("#0f172a"))
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(margin, y, "DATOS DEL CLIENTE")
    y -= 18
    pdf.setFont("Helvetica", 10)
    pdf.setFillColor(HexColor("#334155"))
    cliente_lineas = [
        f"Nombre: {reserva.usuario.get_full_name() or reserva.usuario.username}",
        f"Correo: {reserva.usuario.email or 'No registrado'}",
        f"Empresa: {reserva.usuario.empresa or '—'}",
    ]
    for linea in cliente_lineas:
        pdf.drawString(margin + 10, y, linea)
        y -= 16
    y -= 12

    # Datos del vehículo
    pdf.setFillColor(HexColor("#0f172a"))
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(margin, y, "DATOS DEL VEHÍCULO")
    y -= 18
    pdf.setFont("Helvetica", 10)
    pdf.setFillColor(HexColor("#334155"))
    vehiculo_lineas = [
        f"Vehículo: {reserva.vehiculo.marca} {reserva.vehiculo.modelo}",
        f"Placa: {reserva.vehiculo.placa}",
        f"Categoría: {reserva.vehiculo.categoria.nombre}",
    ]
    for linea in vehiculo_lineas:
        pdf.drawString(margin + 10, y, linea)
        y -= 16
    y -= 12

    # Tabla de facturación
    pdf.setFillColor(HexColor("#0f172a"))
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(margin, y, "DETALLE DE FACTURACIÓN")
    y -= 22

    # Encabezados de tabla
    col_x = [margin + 10, margin + 160, margin + 270, margin + 380]
    col_w = [140, 100, 100, 100]
    headers = ["Concepto", "Inicio", "Fin", "Valor"]
    pdf.setFillColor(HexColor("#1e293b"))
    pdf.setFont("Helvetica-Bold", 9)
    for i, h in enumerate(headers):
        pdf.drawString(col_x[i], y, h)
    y -= 2
    pdf.setStrokeColor(HexColor("#cbd5e1"))
    pdf.line(margin + 10, y, margin + 490, y)
    y -= 16

    # Filas de tabla
    pdf.setFont("Helvetica", 10)
    pdf.setFillColor(HexColor("#334155"))
    rows = [
        ["Tarifa diaria", "", "", f"${reserva.tarifa_diaria:,.2f}"],
        [f"Alquiler ({reserva.dias} día{'s' if reserva.dias != 1 else ''})",
         reserva.fecha_inicio.strftime("%d/%m/%Y"),
         reserva.fecha_fin.strftime("%d/%m/%Y"),
         f"${reserva.total:,.2f}"],
    ]
    for row in rows:
        pdf.drawString(col_x[0], y, row[0])
        pdf.drawString(col_x[1], y, row[1])
        pdf.drawString(col_x[2], y, row[2])
        pdf.drawString(col_x[3], y, row[3])
        y -= 18

    # Total
    pdf.line(margin + 10, y, margin + 490, y)
    y -= 16
    pdf.setFillColor(HexColor("#0f172a"))
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(col_x[0], y, "TOTAL")
    pdf.drawString(col_x[3], y, f"${reserva.total:,.2f}")
    y -= 10
    pdf.setFont("Helvetica", 9)
    pdf.setFillColor(HexColor("#64748b"))
    pdf.drawString(col_x[0], y, "Incluye todos los impuestos y cargos aplicables.")
    y -= 30

    # Estado
    pdf.setFillColor(HexColor("#0f172a"))
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(margin, y, "ESTADO DEL CONTRATO")
    y -= 18
    pdf.setFont("Helvetica", 10)
    pdf.setFillColor(HexColor("#334155"))
    pdf.drawString(margin + 10, y, f"Estado actual: {reserva.get_estado_display()}")
    y -= 30

    # Línea separadora
    pdf.setStrokeColor(HexColor("#cbd5e1"))
    pdf.line(margin, y, width - margin, y)
    y -= 30

    # Firmas
    pdf.setFillColor(HexColor("#0f172a"))
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(margin, y, "FIRMAS")
    y -= 24
    pdf.setFont("Helvetica", 10)
    pdf.setFillColor(HexColor("#334155"))

    # Firma cliente
    pdf.drawString(margin, y, f"Cliente: {reserva.usuario.get_full_name() or reserva.usuario.username}")
    y -= 6
    pdf.line(margin, y - 10, margin + 200, y - 10)
    y_text = y - 26
    pdf.setFont("Helvetica", 8)
    pdf.setFillColor(HexColor("#94a3b8"))
    pdf.drawString(margin, y_text, "Firma del cliente")

    # Firma administrador
    pdf.setFont("Helvetica", 10)
    pdf.setFillColor(HexColor("#334155"))
    pdf.drawString(margin + 250, y + 10, "Administrador FleetFlow")
    pdf.line(margin + 250, y - 10, margin + 490, y - 10)
    pdf.setFont("Helvetica", 8)
    pdf.setFillColor(HexColor("#94a3b8"))
    pdf.drawString(margin + 250, y_text, "Firma del administrador")

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return FileResponse(
        buffer,
        as_attachment=True,
        filename=f"contrato-CTR-{reserva.id:05d}.pdf"
    )


# ============================================================================
# Vistas JSON para gráficos Chart.js - Dashboard
# ============================================================================

@require_http_methods(["GET"])
def grafico_top_vehiculos(request):
    """
    API para gráfico de top 5 vehículos más alquilados.
    Requiere autenticación de administrador.
    """
    user = usuario_autenticado(request)
    if not user or not user.is_staff:
        return respuesta_error("Acceso denegado. Solo administradores.", status=403)

    from django.db.models import Count
    
    # Top 5 vehículos por cantidad de reservas
    top_vehiculos = Vehiculo.objects.annotate(
        num_reservas=Count('reservas')
    ).order_by('-num_reservas')[:5]

    data = {
        "labels": [f"{v.marca} {v.modelo} ({v.placa})" for v in top_vehiculos],
        "datasets": [{
            "label": "Cantidad de Alquileres",
            "data": [v.num_reservas for v in top_vehiculos],
            "backgroundColor": [
                "rgba(99, 102, 241, 0.8)",
                "rgba(139, 92, 246, 0.8)",
                "rgba(168, 85, 247, 0.8)",
                "rgba(236, 72, 153, 0.8)",
                "rgba(244, 63, 94, 0.8)",
            ],
            "borderColor": [
                "rgba(99, 102, 241, 1)",
                "rgba(139, 92, 246, 1)",
                "rgba(168, 85, 247, 1)",
                "rgba(236, 72, 153, 1)",
                "rgba(244, 63, 94, 1)",
            ],
            "borderWidth": 2,
        }]
    }
    return JsonResponse(data)


@require_http_methods(["GET"])
def grafico_ingresos_mensuales(request):
    """
    API para gráfico de ingresos mensuales.
    Requiere autenticación de administrador.
    """
    user = usuario_autenticado(request)
    if not user or not user.is_staff:
        return respuesta_error("Acceso denegado. Solo administradores.", status=403)

    from django.db.models import Sum
    from datetime import datetime, timedelta
    
    # Últimos 12 meses
    hoy = datetime.now().date()
    meses = []
    ingresos = []
    
    for i in range(11, -1, -1):
        fecha_inicio = datetime(hoy.year, hoy.month, 1) - timedelta(days=i*30)
        fecha_inicio = fecha_inicio.replace(day=1)
        
        # Primer día del mes siguiente
        if fecha_inicio.month == 12:
            fecha_fin = fecha_inicio.replace(year=fecha_inicio.year + 1, month=1)
        else:
            fecha_fin = fecha_inicio.replace(month=fecha_inicio.month + 1)
        
        # Ingresos del mes
        reservas_mes = Reserva.objects.filter(
            estado=Reserva.DEVUELTA,
            actualizado__gte=fecha_inicio,
            actualizado__lt=fecha_fin,
        ).aggregate(total=Sum('total'))
        
        mes_nombre = fecha_inicio.strftime("%b %Y")
        meses.append(mes_nombre)
        ingresos.append(float(reservas_mes['total'] or 0))
    
    data = {
        "labels": meses,
        "datasets": [{
            "label": "Ingresos ($)",
            "data": ingresos,
            "borderColor": "rgba(34, 197, 94, 1)",
            "backgroundColor": "rgba(34, 197, 94, 0.1)",
            "borderWidth": 2,
            "fill": True,
            "tension": 0.4,
        }]
    }
    return JsonResponse(data)


@require_http_methods(["GET"])
def grafico_estado_reservas(request):
    """
    API para gráfico de distribución de estados de reservas.
    Requiere autenticación de administrador.
    """
    user = usuario_autenticado(request)
    if not user or not user.is_staff:
        return respuesta_error("Acceso denegado. Solo administradores.", status=403)

    from django.db.models import Count
    
    # Contar reservas por estado
    estados_count = Reserva.objects.values('estado').annotate(
        count=Count('id')
    ).order_by('-count')
    
    labels = []
    data_values = []
    colors = {
        'pendiente': 'rgba(249, 115, 22, 0.8)',
        'confirmada': 'rgba(59, 130, 246, 0.8)',
        'en_alquiler': 'rgba(34, 197, 94, 0.8)',
        'devuelta': 'rgba(139, 92, 246, 0.8)',
        'cancelada': 'rgba(239, 68, 68, 0.8)',
    }
    colores = []
    
    for item in estados_count:
        estado = item['estado']
        count = item['count']
        estado_display = dict(Reserva.ESTADOS).get(estado, estado)
        labels.append(estado_display)
        data_values.append(count)
        colores.append(colors.get(estado, 'rgba(107, 114, 128, 0.8)'))
    
    data = {
        "labels": labels,
        "datasets": [{
            "data": data_values,
            "backgroundColor": colores,
            "borderColor": colores,
            "borderWidth": 2,
        }]
    }
    return JsonResponse(data)
