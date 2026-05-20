# FleetFlow — Gestión de Alquiler de Vehículos

Sistema Django 6.0 para administrar el ciclo completo de alquiler vehicular: catálogo, categorías, tarifas, disponibilidad, reservas, check-in/check-out, contratos PDF, dashboard con gráficos y panel administrativo con control de roles.

## Credenciales predefinidas

| Rol | Email | Contraseña |
|---|---|---|
| Administrador | `admin@fleetflow.com` | `admin` |


## Funcionalidades implementadas

### Autenticación y roles
- Modelo `CustomUser` con campos `role` (`admin` / `cliente`), `empresa`, `teléfono`
- Registro con selección de rol (Administrador o Cliente)
- Login con email y contraseña
- Mixins `AdminRequiredMixin` y `ClienteRequiredMixin` con redirección y mensajes
- Sidebar adaptativa según el rol del usuario

### Catálogo de vehículos (MVT)
- **Administradores**: CRUD completo de vehículos, categorías y tarifas
- **Clientes**: Vista de catálogo con filtros (búsqueda por marca/modelo, categoría)
- Listado paginado con búsqueda y filtros por estado/categoría
- Formularios con widgets Bootstrap y validaciones (placa única, año entre 1980-actual, precio positivo)

### Reservas
- Creación de reservas con validación de fechas
- Prevención de solapamiento (no permite dos reservas activas en el mismo vehículo y rango de fechas)
- Cálculo automático del total (tarifa diaria × días)
- Flujo completo: pendiente → confirmada → en_alquiler → devuelta
- Cancelación de reservas
- Check-in / Check-out con registro de kilometraje
- Vista para clientes: "Mis reservas" con detalle y timeline
- Vista para administradores: listado completo con filtro por estado

### Dashboard y gráficos
- Panel con KPIs (alquileres activos, ingresos, utilización, devoluciones)
- Gráfico de ingresos mensuales (línea) conectado a API real
- Gráfico de distribución por estado de reservas (dona)
- Gráfico de top 5 vehículos más alquilados (barras)
- Alertas operativas
- Dashboard admin con métricas adicionales (flota total, mantenimiento, próximas reservas)

### API REST
- Endpoints JSON para categorías, tarifas, vehículos y reservas
- Endpoints de disponibilidad por fechas
- Endpoints para gráficos (top-vehículos, ingresos-mensuales, estado-reservas)
- Autenticación por sesión o Basic Auth
- Control de permisos: solo administradores pueden crear/editar/eliminar

### Contrato PDF
- Generación dinámica con ReportLab
- Membrete FleetFlow, datos del cliente, vehículo y facturación
- Tabla de conceptos con tarifa diaria, días y total
- Sección de firmas para cliente y administrador
- Descarga con nombre `contrato-CTR-{id}.pdf`

### Interfaz de usuario
- Tema oscuro con glassmorphism (backdrop-filter, gradientes)
- Bootstrap 5.3.7 + Bootstrap Icons + Chart.js 4.4.3
- Sidebar con navegación contextual (admin vs cliente)
- Barra de búsqueda funcional (redirige a vehículos o catálogo según el rol)
- Diseño responsive (3 breakpoints)
- Formularios con estilos coherentes (inputs, selects, checkboxes en modo oscuro)

## Arquitectura

```text
GESTION-ALQUILER-VEHICULOS/
├── manage.py
├── requirements.txt
├── db.sqlite3
├── project/                  # Configuración Django
│   ├── settings.py
│   ├── urls.py               # Rutas raíz
│   ├── forms.py              # Formularios globales
│   ├── ui_views.py           # Vistas MVT (home, login, dashboard, catálogo, contratos)
│   └── image_services.py     # Servicio de imágenes con fallback
├── usuarios/                 # Gestión de usuarios
│   ├── models.py             # CustomUser con roles
│   └── admin.py
├── vehiculo/                 # Catálogo de vehículos
│   ├── models.py             # Categoria, Tarifa, Vehiculo
│   ├── views.py              # API REST vehicular
│   └── urls.py
├── reservas/                 # Proceso de alquiler
│   ├── models.py             # Reserva con clean(), save(), check-in/out
│   ├── views.py              # API REST + PDF + gráficos
│   ├── vistas_mvt.py         # Vistas MVT con control de roles
│   └── urls.py
├── templates/                # Plantillas Django
│   ├── base.html
│   ├── dashboard.html
│   ├── catalogo.html
│   ├── contratos.html
│   ├── login.html / register.html
│   ├── vehiculo/             # CRUD vehículos (6 templates)
│   ├── reservas/             # Reservas (4 templates)
│   ├── dashboard_admin.html  # Dashboard admin
│   └── components/           # navbar, sidebar, messages
└── static/
    ├── css/app.css           # Estilos oscuros con glassmorphism
    ├── js/app.js             # Chart.js conectado a APIs reales
    └── images/               # Placeholder SVG de vehículos
```

## URLs del sistema

### Públicas
| Ruta | Descripción |
|---|---|
| `/` | Landing page |
| `/login/` | Inicio de sesión |
| `/register/` | Registro de usuario |

### Dashboard (autenticado)
| Ruta | Descripción |
|---|---|
| `/dashboard/` | Panel analítico con KPIs y gráficos |
| `/catalogo/` | Catálogo de vehículos |
| `/contratos/` | Gestión de contratos con timeline |

### Admin MVT
| Ruta | Descripción |
|---|---|
| `/admin/vehiculos/` | Lista de vehículos |
| `/admin/vehiculos/crear/` | Nuevo vehículo |
| `/admin/vehiculos/<id>/` | Detalle |
| `/admin/vehiculos/<id>/editar/` | Editar |
| `/admin/vehiculos/<id>/eliminar/` | Eliminar |
| `/admin/categorias/` | Lista de categorías |
| `/admin/categorias/crear/` | Nueva categoría |
| `/admin/categorias/<id>/editar/` | Editar categoría |
| `/admin/reservas/` | Lista de reservas (admin) |
| `/admin/dashboard/` | Dashboard ejecutivo |

### Cliente MVT
| Ruta | Descripción |
|---|---|
| `/catalogo/` | Catálogo para clientes |
| `/mis-reservas/` | Reservas del cliente |
| `/reservar/` | Crear reserva |
| `/reservas/<id>/` | Detalle de reserva |

### API REST
| Ruta | Descripción |
|---|---|
| `GET/POST /api/categorias/` | CRUD categorías |
| `GET/PUT/PATCH/DELETE /api/categorias/<id>/` | Detalle categoría |
| `GET/POST /api/tarifas/` | CRUD tarifas |
| `GET/PUT/PATCH/DELETE /api/tarifas/<id>/` | Detalle tarifa |
| `GET/POST /api/vehiculos/` | CRUD vehículos |
| `GET/PUT/PATCH/DELETE /api/vehiculos/<id>/` | Detalle vehículo |
| `GET /api/vehiculos/<id>/disponibilidad/` | Disponibilidad |
| `GET/POST /api/reservas/` | CRUD reservas |
| `GET/PUT/PATCH/DELETE /api/reservas/<id>/` | Detalle reserva |
| `POST /api/reservas/<id>/check-in/` | Check-in |
| `POST /api/reservas/<id>/check-out/` | Check-out |
| `GET /api/reservas/<id>/contrato.pdf` | Descargar PDF |
| `GET /api/graficos/ingresos-mensuales/` | Ingresos (admin) |
| `GET /api/graficos/top-vehiculos/` | Top vehículos (admin) |
| `GET /api/graficos/estado-reservas/` | Estados (admin) |

### Django Admin
| Ruta | Descripción |
|---|---|
| `/admin/` | Panel administrativo Django |

## Reglas de negocio

- Un vehículo solo puede reservarse si está en estado `disponible`
- No se permiten reservas con fechas solapadas para el mismo vehículo si la reserva existente está activa
- Estados activos para solapamiento: `pendiente`, `confirmada`, `en_alquiler`
- La fecha de fin debe ser posterior a la fecha de inicio
- Días facturados = `fecha_fin - fecha_inicio` (mínimo 1 día)
- Total = días × tarifa_diaria
- Al crear una reserva se toma la tarifa activa de menor precio de la categoría
- Check-in solo para reservas `pendiente` o `confirmada`
- Check-out solo para reservas `en_alquiler`

## Instalación

### Requisitos
- Python 3.13+
- SQLite (desarrollo) o PostgreSQL (producción)

### Pasos

```powershell
python -m venv ambiente
.\ambiente\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Servidor local: http://127.0.0.1:8000/

### Variables de entorno

| Variable | Descripción |
|---|---|
| `DATABASE_URL` | Conexión PostgreSQL (opcional, fallback a SQLite) |
| `SECRET_KEY` | Clave secreta de Django |
| `DEBUG` | `False` en producción |
| `ALLOWED_HOSTS` | Dominios permitidos |

## Validación

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

## Dependencias principales

- `Django==6.0.3`
- `dj-database-url`
- `psycopg[binary]`
- `reportlab`
- `gunicorn`
