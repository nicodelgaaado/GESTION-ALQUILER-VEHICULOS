"""
URL configuration for project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from . import ui_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', ui_views.home, name='home'),
    path('login/', ui_views.login_view, name='login'),
    path('logout/', ui_views.logout_view, name='logout'),
    path('register/', ui_views.register_view, name='register'),
    path('catalogo/', ui_views.catalogo, name='catalogo'),
    path('dashboard/', ui_views.dashboard, name='dashboard'),
    path('contratos/', ui_views.contratos, name='contratos'),
    path('api/hero-image/', ui_views.hero_vehicle_image, name='hero_image'),
    path('api/fleet-stats/', ui_views.fleet_stats, name='fleet_stats'),
    path('api/', include('vehiculo.urls')),
    path('api/', include('reservas.urls')),
]
