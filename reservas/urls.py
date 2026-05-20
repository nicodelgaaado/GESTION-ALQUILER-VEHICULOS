from django.urls import path

from . import views


urlpatterns = [
    path("reservas/", views.reservas, name="api_reservas"),
    path("reservas/reporte.pdf", views.reservas_reporte_pdf, name="api_reservas_reporte_pdf"),
    path("reservas/<int:reserva_id>/", views.reserva_detalle, name="api_reserva_detalle"),
    path("reservas/<int:reserva_id>/check-in/", views.reserva_check_in, name="api_reserva_check_in"),
    path("reservas/<int:reserva_id>/check-out/", views.reserva_check_out, name="api_reserva_check_out"),
    path("reservas/<int:reserva_id>/contrato.pdf", views.reserva_contrato_pdf, name="api_reserva_contrato_pdf"),
    path("graficos/top-vehiculos/", views.grafico_top_vehiculos, name="api_grafico_top_vehiculos"),
    path("graficos/ingresos-mensuales/", views.grafico_ingresos_mensuales, name="api_grafico_ingresos_mensuales"),
    path("graficos/estado-reservas/", views.grafico_estado_reservas, name="api_grafico_estado_reservas"),
]
