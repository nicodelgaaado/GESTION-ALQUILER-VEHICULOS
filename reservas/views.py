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

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 72

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(72, y, "Contrato de Alquiler de Vehiculo")
    y -= 36
    pdf.setFont("Helvetica", 11)
    lineas = [
        f"Contrato No.: {reserva.id}",
        f"Cliente: {reserva.usuario.get_full_name() or reserva.usuario.username}",
        f"Correo: {reserva.usuario.email or 'No registrado'}",
        f"Vehiculo: {reserva.vehiculo.marca} {reserva.vehiculo.modelo}",
        f"Placa: {reserva.vehiculo.placa}",
        f"Categoria: {reserva.vehiculo.categoria.nombre}",
        f"Fecha de inicio: {reserva.fecha_inicio.isoformat()}",
        f"Fecha de fin: {reserva.fecha_fin.isoformat()}",
        f"Dias facturados: {reserva.dias}",
        f"Tarifa diaria: ${reserva.tarifa_diaria}",
        f"Valor total: ${reserva.total}",
        f"Estado: {reserva.get_estado_display()}",
    ]
    for linea in lineas:
        pdf.drawString(72, y, linea)
        y -= 20

    y -= 20
    pdf.line(72, y, width - 72, y)
    y -= 36
    pdf.drawString(72, y, "Firma cliente: ______________________________")
    y -= 36
    pdf.drawString(72, y, "Firma administrador: _________________________")
    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f"contrato-reserva-{reserva.id}.pdf")
