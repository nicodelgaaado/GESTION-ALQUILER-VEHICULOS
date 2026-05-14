from django.urls import path

from . import views


urlpatterns = [
    path("categorias/", views.categorias, name="api_categorias"),
    path("categorias/<int:categoria_id>/", views.categoria_detalle, name="api_categoria_detalle"),
    path("tarifas/", views.tarifas, name="api_tarifas"),
    path("tarifas/<int:tarifa_id>/", views.tarifa_detalle, name="api_tarifa_detalle"),
    path("vehiculos/", views.vehiculos, name="api_vehiculos"),
    path("vehiculos/<int:vehiculo_id>/", views.vehiculo_detalle, name="api_vehiculo_detalle"),
    path(
        "vehiculos/<int:vehiculo_id>/disponibilidad/",
        views.vehiculo_disponibilidad,
        name="api_vehiculo_disponibilidad",
    ),
]
