import json
from decimal import Decimal, InvalidOperation

from django.contrib.auth import authenticate
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import IntegrityError
from django.http import JsonResponse
from django.utils.dateparse import parse_date
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from reservas.models import Reserva
from .models import Categoria, Tarifa, Vehiculo


def respuesta_error(mensaje, status=400, errores=None):
    data = {"error": mensaje}
    if errores:
        data["detalles"] = errores
    return JsonResponse(data, status=status)


def leer_json(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        raise ValueError("El cuerpo de la solicitud debe ser JSON valido.")


def usuario_autenticado(request):
    if request.user.is_authenticated:
        return request.user

    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Basic "):
        return None

    import base64

    try:
        decoded = base64.b64decode(auth.removeprefix("Basic ").strip()).decode("utf-8")
        username, password = decoded.split(":", 1)
    except (ValueError, UnicodeDecodeError):
        return None
    return authenticate(request, username=username, password=password)


def requerir_staff(request):
    user = usuario_autenticado(request)
    return user if user and user.is_staff else None


def decimal_desde_payload(payload, campo):
    try:
        return Decimal(str(payload[campo]))
    except KeyError as exc:
        raise ValueError(f"El campo {campo} es obligatorio.") from exc
    except (InvalidOperation, TypeError) as exc:
        raise ValueError(f"El campo {campo} debe ser numerico.") from exc


def booleano_desde_payload(valor):
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, str):
        if valor.lower() in ["true", "1", "si", "yes"]:
            return True
        if valor.lower() in ["false", "0", "no"]:
            return False
    raise ValueError("El valor booleano debe ser true o false.")


def fecha_desde_query(request, campo):
    valor = request.GET.get(campo)
    fecha = parse_date(valor) if valor else None
    if not fecha:
        raise ValueError(f"El parametro {campo} debe tener formato YYYY-MM-DD.")
    return fecha


def categoria_json(categoria):
    return {
        "id": categoria.id,
        "nombre": categoria.nombre,
        "descripcion": categoria.descripcion,
    }


def tarifa_json(tarifa):
    return {
        "id": tarifa.id,
        "categoria": categoria_json(tarifa.categoria),
        "precio_diario": str(tarifa.precio_diario),
        "activa": tarifa.activa,
    }


def vehiculo_json(vehiculo):
    tarifa = vehiculo.tarifa_activa
    return {
        "id": vehiculo.id,
        "placa": vehiculo.placa,
        "marca": vehiculo.marca,
        "modelo": vehiculo.modelo,
        "anio": vehiculo.anio,
        "categoria": categoria_json(vehiculo.categoria),
        "estado": vehiculo.estado,
        "kilometraje": vehiculo.kilometraje,
        "descripcion": vehiculo.descripcion,
        "tarifa_activa": tarifa_json(tarifa) if tarifa else None,
    }


def aplicar_categoria(categoria, payload):
    categoria.nombre = payload.get("nombre", categoria.nombre)
    categoria.descripcion = payload.get("descripcion", categoria.descripcion)
    categoria.full_clean()
    categoria.save()
    return categoria


def aplicar_tarifa(tarifa, payload):
    if "categoria_id" in payload:
        tarifa.categoria = Categoria.objects.get(pk=payload["categoria_id"])
    if "precio_diario" in payload:
        tarifa.precio_diario = decimal_desde_payload(payload, "precio_diario")
    if "activa" in payload:
        tarifa.activa = booleano_desde_payload(payload["activa"])
    tarifa.full_clean()
    tarifa.save()
    return tarifa


def aplicar_vehiculo(vehiculo, payload):
    for campo in ["placa", "marca", "modelo", "descripcion", "estado"]:
        if campo in payload:
            setattr(vehiculo, campo, payload[campo])
    if "anio" in payload:
        vehiculo.anio = int(payload["anio"])
    if "kilometraje" in payload:
        vehiculo.kilometraje = int(payload["kilometraje"])
    if "categoria_id" in payload:
        vehiculo.categoria = Categoria.objects.get(pk=payload["categoria_id"])
    vehiculo.full_clean()
    vehiculo.save()
    return vehiculo


@csrf_exempt
@require_http_methods(["GET", "POST"])
def categorias(request):
    if request.method == "GET":
        data = [categoria_json(categoria) for categoria in Categoria.objects.all()]
        return JsonResponse({"resultados": data})

    if not requerir_staff(request):
        return respuesta_error("Solo administradores pueden crear categorias.", status=403)

    try:
        categoria = aplicar_categoria(Categoria(), leer_json(request))
    except (ValueError, ValidationError, IntegrityError) as exc:
        return respuesta_error("No se pudo crear la categoria.", errores=str(exc))
    return JsonResponse(categoria_json(categoria), status=201)


@csrf_exempt
@require_http_methods(["GET", "PUT", "PATCH", "DELETE"])
def categoria_detalle(request, categoria_id):
    try:
        categoria = Categoria.objects.get(pk=categoria_id)
    except Categoria.DoesNotExist:
        return respuesta_error("Categoria no encontrada.", status=404)

    if request.method == "GET":
        return JsonResponse(categoria_json(categoria))

    if not requerir_staff(request):
        return respuesta_error("Solo administradores pueden modificar categorias.", status=403)

    if request.method == "DELETE":
        categoria.delete()
        return JsonResponse({}, status=204)

    try:
        categoria = aplicar_categoria(categoria, leer_json(request))
    except (ValueError, ValidationError, IntegrityError) as exc:
        return respuesta_error("No se pudo actualizar la categoria.", errores=str(exc))
    return JsonResponse(categoria_json(categoria))


@csrf_exempt
@require_http_methods(["GET", "POST"])
def tarifas(request):
    if request.method == "GET":
        data = [tarifa_json(tarifa) for tarifa in Tarifa.objects.select_related("categoria")]
        return JsonResponse({"resultados": data})

    if not requerir_staff(request):
        return respuesta_error("Solo administradores pueden crear tarifas.", status=403)

    try:
        payload = leer_json(request)
        tarifa = aplicar_tarifa(Tarifa(), payload)
    except (ValueError, ValidationError, IntegrityError, ObjectDoesNotExist) as exc:
        return respuesta_error("No se pudo crear la tarifa.", errores=str(exc))
    return JsonResponse(tarifa_json(tarifa), status=201)


@csrf_exempt
@require_http_methods(["GET", "PUT", "PATCH", "DELETE"])
def tarifa_detalle(request, tarifa_id):
    try:
        tarifa = Tarifa.objects.select_related("categoria").get(pk=tarifa_id)
    except Tarifa.DoesNotExist:
        return respuesta_error("Tarifa no encontrada.", status=404)

    if request.method == "GET":
        return JsonResponse(tarifa_json(tarifa))

    if not requerir_staff(request):
        return respuesta_error("Solo administradores pueden modificar tarifas.", status=403)

    if request.method == "DELETE":
        tarifa.delete()
        return JsonResponse({}, status=204)

    try:
        tarifa = aplicar_tarifa(tarifa, leer_json(request))
    except (ValueError, ValidationError, IntegrityError, ObjectDoesNotExist) as exc:
        return respuesta_error("No se pudo actualizar la tarifa.", errores=str(exc))
    return JsonResponse(tarifa_json(tarifa))


@csrf_exempt
@require_http_methods(["GET", "POST"])
def vehiculos(request):
    if request.method == "GET":
        queryset = Vehiculo.objects.select_related("categoria").prefetch_related("categoria__tarifas")
        data = [vehiculo_json(vehiculo) for vehiculo in queryset]
        return JsonResponse({"resultados": data})

    if not requerir_staff(request):
        return respuesta_error("Solo administradores pueden crear vehiculos.", status=403)

    try:
        vehiculo = aplicar_vehiculo(Vehiculo(), leer_json(request))
    except (ValueError, ValidationError, IntegrityError, ObjectDoesNotExist) as exc:
        return respuesta_error("No se pudo crear el vehiculo.", errores=str(exc))
    return JsonResponse(vehiculo_json(vehiculo), status=201)


@csrf_exempt
@require_http_methods(["GET", "PUT", "PATCH", "DELETE"])
def vehiculo_detalle(request, vehiculo_id):
    try:
        vehiculo = Vehiculo.objects.select_related("categoria").get(pk=vehiculo_id)
    except Vehiculo.DoesNotExist:
        return respuesta_error("Vehiculo no encontrado.", status=404)

    if request.method == "GET":
        return JsonResponse(vehiculo_json(vehiculo))

    if not requerir_staff(request):
        return respuesta_error("Solo administradores pueden modificar vehiculos.", status=403)

    if request.method == "DELETE":
        vehiculo.delete()
        return JsonResponse({}, status=204)

    try:
        vehiculo = aplicar_vehiculo(vehiculo, leer_json(request))
    except (ValueError, ValidationError, IntegrityError, ObjectDoesNotExist) as exc:
        return respuesta_error("No se pudo actualizar el vehiculo.", errores=str(exc))
    return JsonResponse(vehiculo_json(vehiculo))


@require_http_methods(["GET"])
def vehiculo_disponibilidad(request, vehiculo_id):
    try:
        vehiculo = Vehiculo.objects.get(pk=vehiculo_id)
        fecha_inicio = fecha_desde_query(request, "fecha_inicio")
        fecha_fin = fecha_desde_query(request, "fecha_fin")
    except Vehiculo.DoesNotExist:
        return respuesta_error("Vehiculo no encontrado.", status=404)
    except ValueError as exc:
        return respuesta_error(str(exc))

    if fecha_fin <= fecha_inicio:
        return respuesta_error("La fecha de fin debe ser posterior a la fecha de inicio.")

    disponible_por_reservas = Reserva.vehiculo_disponible(vehiculo, fecha_inicio, fecha_fin)
    disponible = vehiculo.estado == Vehiculo.DISPONIBLE and disponible_por_reservas
    return JsonResponse(
        {
            "vehiculo_id": vehiculo.id,
            "fecha_inicio": fecha_inicio.isoformat(),
            "fecha_fin": fecha_fin.isoformat(),
            "disponible": disponible,
        }
    )
