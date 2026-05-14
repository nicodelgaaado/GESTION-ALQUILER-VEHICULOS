# Gestion de Alquiler de Vehiculos

Sistema Django para administrar el ciclo completo de alquiler de vehiculos: catalogo de vehiculos, categorias, tarifas, disponibilidad, reservas, check-in, check-out y generacion de contrato PDF.

El proyecto corresponde al alcance "Sistema de Gestion de Alquiler de Vehiculos" del trabajo final de Django. La base actual implementa el nucleo tecnico del dominio y deja la estructura lista para ampliar interfaz web, graficos, reportes y despliegue con PostgreSQL.

## Alcance funcional

### Implementado

- Autenticacion con usuarios Django.
- Separacion de permisos:
  - Administradores: usuarios con `is_staff=True`.
  - Clientes: usuarios autenticados normales.
- CRUD JSON de categorias, tarifas y vehiculos.
- Registro de reservas por cliente.
- Control de disponibilidad por fechas.
- Prevencion de doble reserva por solapamiento.
- Calculo automatico del valor total segun dias y tarifa diaria.
- Flujo de alquiler:
  - Check-in para iniciar el alquiler.
  - Check-out para registrar la devolucion.
- Contrato PDF dinamico por reserva.
- Panel administrativo de Django para consultar y gestionar datos.
- Configuracion para PostgreSQL por `DATABASE_URL` con fallback SQLite local.
- Pruebas automatizadas del flujo principal.

### Preparado para extender

- Dashboard administrativo con filtros avanzados y metricas.
- Graficos de autos mas alquilados e ingresos por mes.
- Envio de contratos PDF por correo.
- Interfaz web para clientes y administradores.
- Despliegue en Render o Heroku usando PostgreSQL.

## Arquitectura tecnica

El sistema esta construido con Django 6 y separa el dominio en dos apps principales:

- `vehiculo`: catalogo operativo del negocio.
  - `Categoria`: clasifica vehiculos y agrupa tarifas.
  - `Tarifa`: precio diario activo por categoria.
  - `Vehiculo`: datos de placa, marca, modelo, estado y kilometraje.
- `reservas`: proceso transaccional de alquiler.
  - `Reserva`: usuario, vehiculo, fechas, estado, tarifa aplicada, total y datos de check-in/check-out.

La API REST es nativa de Django, sin Django REST Framework. Las respuestas se entregan en JSON mediante `JsonResponse`, y los contratos se generan en servidor con ReportLab.

## Modelo de datos

### Categoria

Campos principales:

- `nombre`: nombre unico de la categoria.
- `descripcion`: detalle opcional.

### Tarifa

Campos principales:

- `categoria`: relacion con `Categoria`.
- `precio_diario`: valor diario del alquiler.
- `activa`: indica si la tarifa puede usarse para nuevas reservas.

### Vehiculo

Campos principales:

- `placa`: identificador unico del vehiculo.
- `marca`, `modelo`, `anio`.
- `categoria`: relacion con `Categoria`.
- `estado`: `disponible`, `mantenimiento` o `inactivo`.
- `kilometraje`.
- `descripcion`.

### Reserva

Campos principales:

- `usuario`: cliente asociado.
- `vehiculo`: vehiculo reservado.
- `fecha_inicio`, `fecha_fin`.
- `estado`: `pendiente`, `confirmada`, `en_alquiler`, `devuelta` o `cancelada`.
- `tarifa_diaria`: tarifa congelada al momento de reservar.
- `total`: valor calculado automaticamente.
- `check_in`, `check_out`.
- `kilometraje_salida`, `kilometraje_retorno`.

## Reglas de negocio

- Un vehiculo solo puede reservarse si esta en estado `disponible`.
- No se permiten reservas con fechas solapadas para el mismo vehiculo si la reserva existente esta activa.
- Las reservas activas consideradas para disponibilidad son:
  - `pendiente`
  - `confirmada`
  - `en_alquiler`
- La fecha de fin debe ser posterior a la fecha de inicio.
- Los dias facturados se calculan como diferencia entre `fecha_fin` y `fecha_inicio`, con minimo de 1 dia.
- El total se calcula como:

```text
total = dias_facturados * tarifa_diaria
```

- Al crear una reserva se toma la tarifa activa de menor precio de la categoria del vehiculo.
- El check-in solo aplica a reservas `pendiente` o `confirmada`.
- El check-out solo aplica a reservas `en_alquiler`.
- Si se informa kilometraje en check-in/check-out, se actualiza tambien el kilometraje del vehiculo.

## API REST

Los endpoints administrativos requieren un usuario con `is_staff=True`. Las reservas requieren usuario autenticado.

La autenticacion puede hacerse por sesion Django o por Basic Auth en la cabecera `Authorization`.

### Categorias

- `GET /api/categorias/`
- `POST /api/categorias/`
- `GET /api/categorias/<id>/`
- `PATCH /api/categorias/<id>/`
- `PUT /api/categorias/<id>/`
- `DELETE /api/categorias/<id>/`

Ejemplo `POST /api/categorias/`:

```json
{
  "nombre": "SUV",
  "descripcion": "Vehiculos familiares y camionetas"
}
```

### Tarifas

- `GET /api/tarifas/`
- `POST /api/tarifas/`
- `GET /api/tarifas/<id>/`
- `PATCH /api/tarifas/<id>/`
- `PUT /api/tarifas/<id>/`
- `DELETE /api/tarifas/<id>/`

Ejemplo `POST /api/tarifas/`:

```json
{
  "categoria_id": 1,
  "precio_diario": "150000.00",
  "activa": true
}
```

### Vehiculos

- `GET /api/vehiculos/`
- `POST /api/vehiculos/`
- `GET /api/vehiculos/<id>/`
- `PATCH /api/vehiculos/<id>/`
- `PUT /api/vehiculos/<id>/`
- `DELETE /api/vehiculos/<id>/`
- `GET /api/vehiculos/<id>/disponibilidad/?fecha_inicio=YYYY-MM-DD&fecha_fin=YYYY-MM-DD`

Ejemplo `POST /api/vehiculos/`:

```json
{
  "placa": "ABC123",
  "marca": "Toyota",
  "modelo": "RAV4",
  "anio": 2024,
  "categoria_id": 1,
  "estado": "disponible",
  "kilometraje": 1000,
  "descripcion": "Vehiculo automatico"
}
```

### Reservas y alquileres

- `GET /api/reservas/`
- `POST /api/reservas/`
- `GET /api/reservas/<id>/`
- `PATCH /api/reservas/<id>/`
- `PUT /api/reservas/<id>/`
- `DELETE /api/reservas/<id>/`
- `POST /api/reservas/<id>/check-in/`
- `POST /api/reservas/<id>/check-out/`
- `GET /api/reservas/<id>/contrato.pdf`

Ejemplo `POST /api/reservas/`:

```json
{
  "vehiculo_id": 1,
  "fecha_inicio": "2026-06-01",
  "fecha_fin": "2026-06-04"
}
```

Ejemplo `POST /api/reservas/<id>/check-in/`:

```json
{
  "kilometraje_salida": 1200
}
```

Ejemplo `POST /api/reservas/<id>/check-out/`:

```json
{
  "kilometraje_retorno": 1350
}
```

## Panel administrativo

El panel de Django esta disponible en:

```text
/admin/
```

Desde ahi se pueden administrar:

- Categorias
- Tarifas
- Vehiculos
- Reservas
- Usuarios y permisos

Para crear un administrador local:

```powershell
python manage.py createsuperuser
```

## Configuracion del entorno

### Requisitos

- Python 3.14
- PostgreSQL para entorno productivo o despliegue
- SQLite opcional para desarrollo local

### Instalacion local

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### Base de datos PostgreSQL

Configurar `DATABASE_URL`:

```powershell
$env:DATABASE_URL="postgresql://usuario:password@localhost:5432/gestion_alquiler"
```

Si `DATABASE_URL` no existe, el proyecto usa `db.sqlite3` local como fallback de desarrollo.

### Migraciones y servidor

```powershell
python manage.py migrate
python manage.py runserver
```

Servidor local:

```text
http://127.0.0.1:8000/
```

## Validacion tecnica

Comandos recomendados antes de publicar cambios:

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Validaciones cubiertas por pruebas:

- Creacion de catalogo por administrador.
- Reserva con calculo automatico de total.
- Bloqueo de reserva solapada.
- Consulta de disponibilidad.
- Check-in.
- Check-out.
- Descarga de contrato PDF.

## Despliegue

El proyecto esta preparado para desplegarse con PostgreSQL mediante `DATABASE_URL`.

Variables esperadas en despliegue:

- `DATABASE_URL`: conexion PostgreSQL.
- `SECRET_KEY`: clave segura de Django.
- `DEBUG`: `False` en produccion.
- `ALLOWED_HOSTS`: dominios permitidos.

Dependencias principales:

- `Django`
- `dj-database-url`
- `psycopg[binary]`
- `reportlab`
- `gunicorn`

## Estructura principal

```text
GESTION-ALQUILER-VEHICULOS/
  manage.py
  project/
    settings.py
    urls.py
    asgi.py
    wsgi.py
  vehiculo/
    models.py
    views.py
    urls.py
    admin.py
    migrations/
  reservas/
    models.py
    views.py
    urls.py
    admin.py
    tests.py
    migrations/
  requirements.txt
  README.md
```

## Estado del proyecto

La implementacion actual cubre el nucleo backend y administrativo del sistema de alquiler. La siguiente fase natural es construir la interfaz web del cliente/administrador y agregar dashboard con graficos de uso e ingresos.
