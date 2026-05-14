from django.urls import path

from . import views


urlpatterns = [
    path("reservas/", views.reservas, name="api_reservas"),
    path("reservas/<int:reserva_id>/", views.reserva_detalle, name="api_reserva_detalle"),
    path("reservas/<int:reserva_id>/check-in/", views.reserva_check_in, name="api_reserva_check_in"),
    path("reservas/<int:reserva_id>/check-out/", views.reserva_check_out, name="api_reserva_check_out"),
    path("reservas/<int:reserva_id>/contrato.pdf", views.reserva_contrato_pdf, name="api_reserva_contrato_pdf"),
]
