"""
Modelos personalizados de usuario para gestión de roles y acceso.
Implementa un CustomUser con soporte para roles ADMIN y CLIENTE.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    """Usuario personalizado con soporte para roles de acceso."""
    
    ROLE_ADMIN = 'admin'
    ROLE_CLIENTE = 'cliente'
    
    ROLE_CHOICES = [
        (ROLE_ADMIN, 'Administrador'),
        (ROLE_CLIENTE, 'Cliente'),
    ]
    
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_CLIENTE,
        help_text='Rol del usuario en el sistema'
    )
    empresa = models.CharField(
        max_length=150,
        blank=True,
        help_text='Nombre de la empresa (opcional)'
    )
    telefono = models.CharField(
        max_length=20,
        blank=True,
        help_text='Número de teléfono de contacto'
    )
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-creado']
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
    
    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"
    
    @property
    def es_admin(self):
        """Verificar si el usuario es administrador."""
        return self.role == self.ROLE_ADMIN or self.is_staff or self.is_superuser
    
    @property
    def es_cliente(self):
        """Verificar si el usuario es cliente."""
        return self.role == self.ROLE_CLIENTE and not self.is_staff and not self.is_superuser
    
    def save(self, *args, **kwargs):
        """Al guardar, sincronizar role con is_staff para compatibilidad."""
        if self.is_superuser or self.is_staff or self.role == self.ROLE_ADMIN:
            self.role = self.ROLE_ADMIN
            self.is_staff = True
        elif self.role == self.ROLE_CLIENTE:
            self.is_staff = False
        super().save(*args, **kwargs)
