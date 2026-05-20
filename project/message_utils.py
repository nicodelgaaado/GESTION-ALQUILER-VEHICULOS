"""
Utilidades para el sistema de mensajes de Django.
Proporciona funciones auxiliares para mostrar alertas consistentes.
"""

from django.contrib import messages


def mensaje_exito(request, titulo, descripcion=""):
    """Agregar mensaje de éxito."""
    msg = f"{titulo}"
    if descripcion:
        msg += f" - {descripcion}"
    messages.success(request, msg)


def mensaje_error(request, titulo, descripcion=""):
    """Agregar mensaje de error."""
    msg = f"{titulo}"
    if descripcion:
        msg += f" - {descripcion}"
    messages.error(request, msg)


def mensaje_advertencia(request, titulo, descripcion=""):
    """Agregar mensaje de advertencia."""
    msg = f"{titulo}"
    if descripcion:
        msg += f" - {descripcion}"
    messages.warning(request, msg)


def mensaje_info(request, titulo, descripcion=""):
    """Agregar mensaje de información."""
    msg = f"{titulo}"
    if descripcion:
        msg += f" - {descripcion}"
    messages.info(request, msg)
