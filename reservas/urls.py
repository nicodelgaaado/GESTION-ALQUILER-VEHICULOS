from django.urls import path

from . import views
from .vistas_mvt import (
    VehiculoListView, VehiculoDetailView, VehiculoCreateView,
    VehiculoUpdateView, VehiculoDeleteView,
    CategoriaListView, CategoriaCreateView, CategoriaUpdateView,
    ReservaListAdminView, DashboardAdminView,
    CatalogoClienteView, MisReservasView, ReservaCreateClienteView,
    DetalleReservaClienteView,
)


# API REST (endpoints nativos Django)
urlpatterns = [
    path("api/reservas/", views.reservas, name="api_reservas"),
    path("api/reservas/<int:reserva_id>/", views.reserva_detalle, name="api_reserva_detalle"),
    path("api/reservas/<int:reserva_id>/check-in/", views.reserva_check_in, name="api_reserva_check_in"),
    path("api/reservas/<int:reserva_id>/check-out/", views.reserva_check_out, name="api_reserva_check_out"),
    path("api/reservas/<int:reserva_id>/contrato.pdf", views.reserva_contrato_pdf, name="api_reserva_contrato_pdf"),
    
    # Endpoints para gráficos
    path("api/graficos/top-vehiculos/", views.grafico_top_vehiculos, name="api_grafico_top_vehiculos"),
    path("api/graficos/ingresos-mensuales/", views.grafico_ingresos_mensuales, name="api_grafico_ingresos_mensuales"),
    path("api/graficos/estado-reservas/", views.grafico_estado_reservas, name="api_grafico_estado_reservas"),
]

# Vistas MVT - Admin (Vehículos)
urlpatterns += [
    path("admin/vehiculos/", VehiculoListView.as_view(), name="vehiculo_list"),
    path("admin/vehiculos/<int:pk>/", VehiculoDetailView.as_view(), name="vehiculo_detail"),
    path("admin/vehiculos/crear/", VehiculoCreateView.as_view(), name="vehiculo_create"),
    path("admin/vehiculos/<int:pk>/editar/", VehiculoUpdateView.as_view(), name="vehiculo_update"),
    path("admin/vehiculos/<int:pk>/eliminar/", VehiculoDeleteView.as_view(), name="vehiculo_delete"),
]

# Vistas MVT - Admin (Categorías)
urlpatterns += [
    path("admin/categorias/", CategoriaListView.as_view(), name="categoria_list"),
    path("admin/categorias/crear/", CategoriaCreateView.as_view(), name="categoria_create"),
    path("admin/categorias/<int:pk>/editar/", CategoriaUpdateView.as_view(), name="categoria_update"),
]

# Vistas MVT - Admin (Reservas y Dashboard)
urlpatterns += [
    path("admin/reservas/", ReservaListAdminView.as_view(), name="reserva_list_admin"),
    path("admin/dashboard/", DashboardAdminView.as_view(), name="dashboard_admin"),
]

# Vistas MVT - Clientes
urlpatterns += [
    path("catalogo/", CatalogoClienteView.as_view(), name="catalogo_cliente"),
    path("mis-reservas/", MisReservasView.as_view(), name="mis_reservas"),
    path("reservar/", ReservaCreateClienteView.as_view(), name="reserva_create"),
    path("reservas/<int:pk>/", DetalleReservaClienteView.as_view(), name="reserva_detail_cliente"),
]
