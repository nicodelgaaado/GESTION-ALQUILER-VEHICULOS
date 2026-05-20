"""
Vistas MVT protegidas por roles para el sistema de alquiler de vehículos.
Implementa LoginRequiredMixin y UserPassesTestMixin para control de acceso.

Estructura:
- Vistas para Administradores: CRUD completo de vehículos y reservas
- Vistas para Clientes: Visualización de catálogo y gestión de propias reservas
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
)
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import timedelta

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['show_sidebar'] = True
        return context


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin, SidebarContextMixin):
    """Mixin que verifica si el usuario es administrador."""
    
    def test_func(self):
        return self.request.user.es_admin
    
    def handle_no_permission(self):
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
    
    model = Vehiculo
    template_name = 'vehiculo/vehiculo_confirm_delete.html'
    success_url = reverse_lazy('vehiculo_list')

    def delete(self, request, *args, **kwargs):
        vehiculo = self.get_object()
        placa = vehiculo.placa
        response = super().delete(request, *args, **kwargs)
        messages.success(
            request,
            f'Vehículo {placa} eliminado exitosamente.'
        )
        return response


# ============================================================================
# Vistas para Administradores - Categorías
# ============================================================================

class CategoriaListView(AdminRequiredMixin, ListView):
    """Lista de categorías."""
    
    model = Categoria
    template_name = 'vehiculo/categoria_list.html'
    context_object_name = 'categorias'


class CategoriaCreateView(AdminRequiredMixin, CreateView):
    """Crear categoría."""
    
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


# ============================================================================
# Vistas para Administradores - Reservas y Dashboard
# ============================================================================

class ReservaListAdminView(AdminRequiredMixin, ListView):
    """Lista de todas las reservas (admin)."""
    
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
        
        return queryset.order_by('-fecha_inicio', '-creado')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['estados'] = Reserva.ESTADOS
        context['estado_filter'] = self.request.GET.get('estado', '')
        context['activas'] = Reserva.objects.filter(
            estado__in=Reserva.ESTADOS_ACTIVOS
        ).count()
        return context


class DashboardAdminView(AdminRequiredMixin, TemplateView):
    """Dashboard para administradores con métricas clave."""
    
    template_name = 'dashboard_admin.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoy = timezone.now().date()
        hace_30_dias = hoy - timedelta(days=30)
        
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
    
    model = Reserva
    form_class = ReservaFormCliente
    template_name = 'reservas/crear_reserva.html'
    success_url = reverse_lazy('mis_reservas')

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
