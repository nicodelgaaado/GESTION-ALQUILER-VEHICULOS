"""
Configuración del panel de administración para usuarios.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    """Admin personalizado para CustomUser."""
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Información Adicional', {
            'fields': ('role', 'empresa', 'telefono')
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Información Adicional', {
            'fields': ('role', 'empresa', 'telefono')
        }),
    )
    
    list_display = ('email', 'get_nombre_completo', 'role', 'empresa', 'es_activo')
    list_filter = BaseUserAdmin.list_filter + ('role', 'creado')
    search_fields = ('email', 'first_name', 'last_name', 'empresa')
    ordering = ('-creado',)
    
    def get_nombre_completo(self, obj):
        """Mostrar nombre completo del usuario."""
        return obj.get_full_name() or obj.username
    get_nombre_completo.short_description = 'Nombre Completo'
    
    def es_activo(self, obj):
        """Mostrar estado activo del usuario."""
        return '✓' if obj.is_active else '✗'
    es_activo.short_description = 'Activo'
