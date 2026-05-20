"""
Vistas MVT protegidas por roles para el sistema de alquiler de vehículos.
Implementa LoginRequiredMixin y UserPassesTestMixin para control de acceso.

Estructura:
- Vistas para Administradores: CRUD completo de vehículos y reservas
- Vistas para Clientes: Visualización de catálogo y gestión de propias reservas
"""

from datetime import timedelta
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import ValidationError
from django.db.models import Q, Sum, Count
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
)
from django.utils import timezone

from vehiculo.models import Vehiculo, Categoria, Tarifa
from reservas.models import Reserva
from project.forms import (
    VehiculoForm, CategoriaForm, TarifaForm, 
    ReservaForm, ReservaFormCliente
)


# ============================================================================
# Mixins personalizados para control de acceso
# ============================================================================

class SidebarContextMixin:
    """Mixin que agrega show_sidebar=True al contexto."""

    active_page = "dashboard"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        is_admin = self.request.user.is_authenticated and self.request.user.es_admin
        context['show_sidebar'] = True
        context['active_page'] = self.active_page
        context['is_admin'] = is_admin
        context['is_client'] = self.request.user.is_authenticated and not is_admin
        context['account_role'] = "Administrador" if is_admin else "Cliente"
        return context


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin, SidebarContextMixin):
    """Mixin que verifica si el usuario es administrador."""
    
    def test_func(self):
        return self.request.user.es_admin
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        messages.error(
            self.request,
            'Acceso denegado. Solo administradores pueden acceder.'
        )
        return redirect('home')


class ClienteRequiredMixin(LoginRequiredMixin, UserPassesTestMixin, SidebarContextMixin):
    """Mixin que verifica si el usuario es cliente."""
    
    def test_func(self):
        return self.request.user.es_cliente
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        messages.error(
            self.request,
            'Acceso denegado. Solo clientes pueden acceder.'
        )
        return redirect('home')


# ============================================================================
# Vistas para Administradores - Vehículos
# ============================================================================

class VehiculoListView(AdminRequiredMixin, ListView):
    """Lista de todos los vehículos (solo admin)."""
    
    active_page = "catalogo"
    model = Vehiculo
    template_name = 'vehiculo/vehiculo_list.html'
    context_object_name = 'vehiculos'
    paginate_by = 15

    def get_queryset(self):
        """Filtrar vehículos según búsqueda y filtros."""
        queryset = Vehiculo.objects.select_related('categoria').all()
        
        # Búsqueda por placa, marca o modelo
        search = self.request.GET.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(placa__icontains=search) |
                Q(marca__icontains=search) |
                Q(modelo__icontains=search)
            )
        
        # Filtro por estado
        estado = self.request.GET.get('estado', '').strip()
        if estado:
            queryset = queryset.filter(estado=estado)
        
        # Filtro por categoría
        categoria = self.request.GET.get('categoria', '').strip()
        if categoria:
            queryset = queryset.filter(categoria__nombre=categoria)
        
        return queryset.order_by('placa')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categorias'] = Categoria.objects.all()
        context['estados'] = Vehiculo.ESTADOS
        context['search'] = self.request.GET.get('search', '')
        context['estado_filter'] = self.request.GET.get('estado', '')
        context['categoria_filter'] = self.request.GET.get('categoria', '')
        return context


class VehiculoDetailView(AdminRequiredMixin, DetailView):
    """Detalle de un vehículo."""
    
    active_page = "catalogo"
    model = Vehiculo
    template_name = 'vehiculo/vehiculo_detail.html'
    context_object_name = 'vehiculo'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vehiculo = self.get_object()
        
        # Próximas reservas
        context['proximas_reservas'] = Reserva.objects.filter(
            vehiculo=vehiculo,
            estado__in=Reserva.ESTADOS_ACTIVOS,
            fecha_inicio__gte=timezone.now().date()
        ).order_by('fecha_inicio')[:5]
        
        # Historial de reservas
        context['historial'] = Reserva.objects.filter(
            vehiculo=vehiculo
        ).order_by('-fecha_inicio')[:10]
        
        return context


class VehiculoCreateView(AdminRequiredMixin, CreateView):
    """Crear nuevo vehículo."""
    
    active_page = "catalogo"
    model = Vehiculo
    form_class = VehiculoForm
    template_name = 'vehiculo/vehiculo_form.html'
    success_url = reverse_lazy('vehiculo_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Vehículo {self.object.placa} creado exitosamente.'
        )
        return response


class VehiculoUpdateView(AdminRequiredMixin, UpdateView):
    """Editar vehículo."""
    
    active_page = "catalogo"
    model = Vehiculo
    form_class = VehiculoForm
    template_name = 'vehiculo/vehiculo_form.html'
    success_url = reverse_lazy('vehiculo_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Vehículo {self.object.placa} actualizado exitosamente.'
        )
        return response


class VehiculoDeleteView(AdminRequiredMixin, DeleteView):
    """Eliminar vehículo."""
    
    active_page = "catalogo"
    model = Vehiculo
    template_name = 'vehiculo/vehiculo_confirm_delete.html'
    success_url = reverse_lazy('vehiculo_list')

    def form_valid(self, form):
        vehiculo = self.get_object()
        placa = vehiculo.placa
        try:
            response = super().form_valid(form)
            messages.success(self.request, f'Vehículo {placa} eliminado exitosamente.')
            return response
        except ProtectedError:
            messages.error(self.request, f'No se puede eliminar {placa} porque tiene reservas asociadas.')
            return redirect(self.success_url)


# ============================================================================
# Vistas para Administradores - Categorías
# ============================================================================

class CategoriaListView(AdminRequiredMixin, ListView):
    """Lista de categorías."""
    
    active_page = "catalogo"
    model = Categoria
    template_name = 'vehiculo/categoria_list.html'
    context_object_name = 'categorias'


class CategoriaCreateView(AdminRequiredMixin, CreateView):
    """Crear categoría."""
    
    active_page = "catalogo"
    model = Categoria
    form_class = CategoriaForm
    template_name = 'vehiculo/categoria_form.html'
    success_url = reverse_lazy('categoria_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Categoría {self.object.nombre} creada exitosamente.'
        )
        return response


class CategoriaUpdateView(AdminRequiredMixin, UpdateView):
    """Editar categoría."""
    
    active_page = "catalogo"
    model = Categoria
    form_class = CategoriaForm
    template_name = 'vehiculo/categoria_form.html'
    success_url = reverse_lazy('categoria_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Categoría {self.object.nombre} actualizada exitosamente.'
        )
        return response


class CategoriaDeleteView(AdminRequiredMixin, DeleteView):
    """Eliminar categoría si no tiene datos dependientes."""

    active_page = "catalogo"
    model = Categoria
    template_name = 'vehiculo/categoria_confirm_delete.html'
    success_url = reverse_lazy('categoria_list')

    def form_valid(self, form):
        categoria = self.get_object()
        try:
            response = super().form_valid(form)
            messages.success(self.request, f'Categoría {categoria.nombre} eliminada exitosamente.')
            return response
        except ProtectedError:
            messages.error(
                self.request,
                f'No se puede eliminar {categoria.nombre} porque tiene vehículos asociados.'
            )
            return redirect(self.success_url)


class TarifaListView(AdminRequiredMixin, ListView):
    """Lista de tarifas configuradas por categoría."""

    active_page = "catalogo"
    model = Tarifa
    template_name = 'vehiculo/tarifa_list.html'
    context_object_name = 'tarifas'
    paginate_by = 20

    def get_queryset(self):
        queryset = Tarifa.objects.select_related('categoria')
        categoria = self.request.GET.get('categoria', '').strip()
        estado = self.request.GET.get('estado', '').strip()
        if categoria:
            queryset = queryset.filter(categoria_id=categoria)
        if estado in ['activa', 'inactiva']:
            queryset = queryset.filter(activa=estado == 'activa')
        return queryset.order_by('categoria__nombre', '-activa', 'precio_diario')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categorias'] = Categoria.objects.all()
        context['categoria_filter'] = self.request.GET.get('categoria', '')
        context['estado_filter'] = self.request.GET.get('estado', '')
        return context


class TarifaCreateView(AdminRequiredMixin, CreateView):
    """Crear nueva tarifa."""

    active_page = "catalogo"
    model = Tarifa
    form_class = TarifaForm
    template_name = 'vehiculo/tarifa_form.html'
    success_url = reverse_lazy('tarifa_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Tarifa creada exitosamente.')
        return response


class TarifaUpdateView(AdminRequiredMixin, UpdateView):
    """Editar tarifa."""

    active_page = "catalogo"
    model = Tarifa
    form_class = TarifaForm
    template_name = 'vehiculo/tarifa_form.html'
    success_url = reverse_lazy('tarifa_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Tarifa actualizada exitosamente.')
        return response


class TarifaDeleteView(AdminRequiredMixin, DeleteView):
    """Eliminar tarifa."""

    active_page = "catalogo"
    model = Tarifa
    template_name = 'vehiculo/tarifa_confirm_delete.html'
    success_url = reverse_lazy('tarifa_list')

    def form_valid(self, form):
        tarifa = self.get_object()
        categoria = tarifa.categoria.nombre
        response = super().form_valid(form)
        messages.success(self.request, f'Tarifa de {categoria} eliminada exitosamente.')
        return response


# ============================================================================
# Vistas para Administradores - Reservas y Dashboard
# ============================================================================

class ReservaListAdminView(AdminRequiredMixin, ListView):
    """Lista de todas las reservas (admin)."""
    
    active_page = "contratos"
    model = Reserva
    template_name = 'reservas/reserva_list_admin.html'
    context_object_name = 'reservas'
    paginate_by = 20

    def get_queryset(self):
        """Filtrar reservas por estado y fechas."""
        queryset = Reserva.objects.select_related(
            'usuario', 'vehiculo', 'vehiculo__categoria'
        ).all()
        
        # Filtro por estado
        estado = self.request.GET.get('estado', '').strip()
        if estado:
            queryset = queryset.filter(estado=estado)

        categoria = self.request.GET.get('categoria', '').strip()
        if categoria:
            queryset = queryset.filter(vehiculo__categoria_id=categoria)

        search = self.request.GET.get('search', '').strip()
        if search:
            search_filter = (
                Q(usuario__username__icontains=search) |
                Q(usuario__email__icontains=search) |
                Q(usuario__first_name__icontains=search) |
                Q(usuario__last_name__icontains=search) |
                Q(vehiculo__placa__icontains=search) |
                Q(vehiculo__marca__icontains=search) |
                Q(vehiculo__modelo__icontains=search)
            )
            normalized = search.upper().replace("CTR-", "").strip()
            if normalized.isdigit():
                search_filter |= Q(pk=int(normalized))
            queryset = queryset.filter(search_filter)

        fecha_inicio = self.request.GET.get('fecha_inicio', '').strip()
        if fecha_inicio:
            queryset = queryset.filter(fecha_inicio__gte=fecha_inicio)

        fecha_fin = self.request.GET.get('fecha_fin', '').strip()
        if fecha_fin:
            queryset = queryset.filter(fecha_fin__lte=fecha_fin)
        
        return queryset.order_by('-fecha_inicio', '-creado')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['estados'] = Reserva.ESTADOS
        context['categorias'] = Categoria.objects.all()
        context['estado_filter'] = self.request.GET.get('estado', '')
        context['categoria_filter'] = self.request.GET.get('categoria', '')
        context['fecha_inicio_filter'] = self.request.GET.get('fecha_inicio', '')
        context['fecha_fin_filter'] = self.request.GET.get('fecha_fin', '')
        context['search'] = self.request.GET.get('search', '')
        context['report_url'] = f"{reverse('api_reservas_reporte_pdf')}?{urlencode(self.request.GET)}"
        context['activas'] = Reserva.objects.filter(
            estado__in=Reserva.ESTADOS_ACTIVOS
        ).count()
        return context

    def post(self, request, *args, **kwargs):
        reserva = get_object_or_404(
            Reserva.objects.select_related('vehiculo', 'usuario'),
            pk=request.POST.get('reserva_id'),
        )
        action = request.POST.get('action')
        try:
            if action == 'approve' and reserva.estado == Reserva.PENDIENTE:
                reserva.estado = Reserva.CONFIRMADA
                reserva.save(update_fields=['estado', 'actualizado'])
                messages.success(request, f'Reserva CTR-{reserva.id:05d} aprobada.')
            elif action == 'check_in' and reserva.estado in [Reserva.PENDIENTE, Reserva.CONFIRMADA]:
                reserva.registrar_check_in(reserva.vehiculo.kilometraje)
                messages.success(request, f'Check-in registrado para CTR-{reserva.id:05d}.')
            elif action == 'check_out' and reserva.estado == Reserva.EN_ALQUILER:
                reserva.registrar_check_out(reserva.vehiculo.kilometraje)
                messages.success(request, f'Check-out registrado para CTR-{reserva.id:05d}.')
            elif action == 'cancel' and reserva.estado not in [Reserva.EN_ALQUILER, Reserva.DEVUELTA, Reserva.CANCELADA]:
                reserva.estado = Reserva.CANCELADA
                reserva.save(update_fields=['estado', 'actualizado'])
                messages.info(request, f'Reserva CTR-{reserva.id:05d} cancelada.')
            else:
                messages.warning(request, 'La acción solicitada no está disponible para esta reserva.')
        except ValidationError as exc:
            messages.error(request, f'No se pudo ejecutar la acción: {exc}')
        query = self.request.GET.urlencode()
        return redirect(f"{reverse('reserva_list_admin')}{'?' + query if query else ''}")


class ReservaDetailAdminView(AdminRequiredMixin, DetailView):
    """Detalle administrativo de una reserva."""

    active_page = "contratos"
    model = Reserva
    template_name = 'reservas/reserva_detail_admin.html'
    context_object_name = 'reserva'

    def get_queryset(self):
        return Reserva.objects.select_related('usuario', 'vehiculo', 'vehiculo__categoria')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        reserva = self.get_object()
        context['puede_cancelar'] = reserva.estado not in [
            Reserva.EN_ALQUILER,
            Reserva.DEVUELTA,
            Reserva.CANCELADA,
        ]
        context['puede_editar'] = reserva.estado not in [Reserva.DEVUELTA, Reserva.CANCELADA]
        return context


class ReservaCreateAdminView(AdminRequiredMixin, CreateView):
    """Crear una reserva desde el panel administrativo."""

    active_page = "contratos"
    model = Reserva
    form_class = ReservaForm
    template_name = 'reservas/reserva_form_admin.html'
    success_url = reverse_lazy('reserva_list_admin')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Reserva CTR-{self.object.id:05d} creada exitosamente.')
        return response


class ReservaUpdateAdminView(AdminRequiredMixin, UpdateView):
    """Editar los datos administrativos de una reserva."""

    active_page = "contratos"
    model = Reserva
    form_class = ReservaForm
    template_name = 'reservas/reserva_form_admin.html'
    success_url = reverse_lazy('reserva_list_admin')

    def get_queryset(self):
        return Reserva.objects.select_related('usuario', 'vehiculo', 'vehiculo__categoria')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Reserva CTR-{self.object.id:05d} actualizada exitosamente.')
        return response


class ReservaDeleteAdminView(AdminRequiredMixin, DetailView):
    """Cancela una reserva desde la ruta de eliminación administrativa."""

    active_page = "contratos"
    model = Reserva
    template_name = 'reservas/reserva_confirm_cancel.html'
    context_object_name = 'reserva'
    success_url = reverse_lazy('reserva_list_admin')

    def get_queryset(self):
        return Reserva.objects.select_related('usuario', 'vehiculo', 'vehiculo__categoria')

    def post(self, request, *args, **kwargs):
        reserva = self.get_object()
        if reserva.estado in [Reserva.EN_ALQUILER, Reserva.DEVUELTA, Reserva.CANCELADA]:
            messages.warning(
                request,
                'Esta reserva no puede cancelarse desde eliminación porque ya está en alquiler, devuelta o cancelada.',
            )
            return redirect('reserva_detail_admin', pk=reserva.pk)
        reserva.estado = Reserva.CANCELADA
        reserva.save(update_fields=['estado', 'actualizado'])
        messages.info(request, f'Reserva CTR-{reserva.id:05d} cancelada. Se conserva en historial.')
        return redirect(self.success_url)


class DashboardAdminView(AdminRequiredMixin, TemplateView):
    """Dashboard para administradores con métricas clave."""
    
    active_page = "dashboard"
    template_name = 'dashboard_admin.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoy = timezone.now().date()
        hace_30_dias = timezone.now() - timedelta(days=30)
        
        # Métricas generales
        context['total_vehiculos'] = Vehiculo.objects.count()
        context['vehiculos_disponibles'] = Vehiculo.objects.filter(
            estado=Vehiculo.DISPONIBLE
        ).count()
        context['vehiculos_en_mantenimiento'] = Vehiculo.objects.filter(
            estado=Vehiculo.MANTENIMIENTO
        ).count()
        
        # Reservas
        context['reservas_activas'] = Reserva.objects.filter(
            estado__in=Reserva.ESTADOS_ACTIVOS
        ).count()
        context['reservas_ultimos_30_dias'] = Reserva.objects.filter(
            creado__gte=hace_30_dias
        ).count()
        
        # Ingresos
        ingresos = Reserva.objects.filter(
            estado=Reserva.DEVUELTA,
            actualizado__gte=hace_30_dias
        ).aggregate(total=Sum('total'))
        context['ingresos_30_dias'] = ingresos['total'] or 0
        
        # Vehículos más alquilados
        context['top_vehiculos'] = Vehiculo.objects.annotate(
            num_reservas=Count('reservas')
        ).order_by('-num_reservas')[:5]
        
        # Reservas próximas
        context['proximas_reservas'] = Reserva.objects.filter(
            estado__in=Reserva.ESTADOS_ACTIVOS,
            fecha_inicio__gte=hoy,
            fecha_inicio__lte=hoy + timedelta(days=7)
        ).select_related('vehiculo', 'usuario').order_by('fecha_inicio')[:10]
        
        return context


# ============================================================================
# Vistas para Clientes - Catálogo y Reservas Propias
# ============================================================================

class CatalogoClienteView(LoginRequiredMixin, SidebarContextMixin, ListView):
    """Catálogo de vehículos disponibles para clientes."""
    
    active_page = "catalogo"
    model = Vehiculo
    template_name = 'vehiculo/catalogo_cliente.html'
    context_object_name = 'vehiculos'
    paginate_by = 12

    def get_queryset(self):
        """Solo mostrar vehículos disponibles."""
        queryset = Vehiculo.objects.filter(
            estado=Vehiculo.DISPONIBLE
        ).select_related('categoria').all()
        
        # Búsqueda y filtros
        search = self.request.GET.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(marca__icontains=search) |
                Q(modelo__icontains=search) |
                Q(placa__icontains=search)
            )
        
        categoria = self.request.GET.get('categoria', '').strip()
        if categoria:
            queryset = queryset.filter(categoria__nombre=categoria)
        
        return queryset.order_by('marca', 'modelo')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categorias'] = Categoria.objects.all()
        context['search'] = self.request.GET.get('search', '')
        context['categoria_filter'] = self.request.GET.get('categoria', '')
        return context


class MisReservasView(LoginRequiredMixin, SidebarContextMixin, ListView):
    """Lista de reservas del cliente autenticado."""
    
    active_page = "mis_reservas"
    model = Reserva
    template_name = 'reservas/mis_reservas.html'
    context_object_name = 'reservas'
    paginate_by = 10

    def get_queryset(self):
        """Solo mostrar reservas del usuario actual."""
        return Reserva.objects.filter(
            usuario=self.request.user
        ).select_related('vehiculo', 'vehiculo__categoria').order_by('-fecha_inicio')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['activas'] = Reserva.objects.filter(
            usuario=self.request.user,
            estado__in=Reserva.ESTADOS_ACTIVOS
        ).count()
        context['historial'] = Reserva.objects.filter(
            usuario=self.request.user,
            estado=Reserva.DEVUELTA
        ).count()
        return context


class ReservaCreateClienteView(LoginRequiredMixin, SidebarContextMixin, CreateView):
    """Crear nueva reserva (cliente)."""
    
    active_page = "catalogo"
    model = Reserva
    form_class = ReservaFormCliente
    template_name = 'reservas/crear_reserva.html'
    success_url = reverse_lazy('mis_reservas')

    def get_initial(self):
        initial = super().get_initial()
        vehiculo_id = self.request.GET.get('vehiculo')
        if vehiculo_id and vehiculo_id.isdigit():
            initial['vehiculo'] = vehiculo_id
        return initial

    def form_valid(self, form):
        """Asignar el usuario actual a la reserva."""
        form.instance.usuario = self.request.user
        response = super().form_valid(form)
        messages.success(
            self.request,
            'Reserva creada exitosamente. Por favor, confirma los detalles.'
        )
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['vehiculos_disponibles'] = Vehiculo.objects.filter(
            estado=Vehiculo.DISPONIBLE
        ).count()
        return context


class DetalleReservaClienteView(LoginRequiredMixin, SidebarContextMixin, DetailView):
    """Detalle de una reserva del cliente."""
    
    active_page = "mis_reservas"
    model = Reserva
    template_name = 'reservas/detalle_reserva.html'
    context_object_name = 'reserva'

    def get_queryset(self):
        """Solo mostrar reservas propias."""
        return Reserva.objects.filter(
            usuario=self.request.user
        ).select_related('vehiculo', 'vehiculo__categoria', 'usuario')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        reserva = self.get_object()
        context['dias_restantes'] = (reserva.fecha_fin - timezone.now().date()).days
        context['puede_cancelar'] = reserva.estado != Reserva.EN_ALQUILER
        return context
