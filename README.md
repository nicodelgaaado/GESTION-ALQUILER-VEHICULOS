# Gestion de Alquiler de Vehiculos

Backend Django para administrar vehiculos, categorias, tarifas, reservas, alquileres y devoluciones. Incluye API REST nativa, calculo automatico de costos, control de disponibilidad y generacion de contrato PDF.

## Requisitos

- Python 3.14
- PostgreSQL para despliegue o desarrollo con `DATABASE_URL`
- SQLite como fallback local si no se define `DATABASE_URL`

## Instalacion

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Configurar PostgreSQL con variable de entorno:

```powershell
$env:DATABASE_URL="postgresql://usuario:password@localhost:5432/gestion_alquiler"
```

Si no se configura `DATABASE_URL`, Django usa `db.sqlite3` local solo para desarrollo.

## Ejecucion

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Validaciones:

```powershell
python manage.py check
python manage.py test
```

## API principal

Los endpoints administrativos requieren un usuario con `is_staff=True`. Las reservas requieren usuario autenticado.

- `GET/POST /api/categorias/`
- `GET/PATCH/DELETE /api/categorias/<id>/`
- `GET/POST /api/tarifas/`
- `GET/PATCH/DELETE /api/tarifas/<id>/`
- `GET/POST /api/vehiculos/`
- `GET/PATCH/DELETE /api/vehiculos/<id>/`
- `GET /api/vehiculos/<id>/disponibilidad/?fecha_inicio=YYYY-MM-DD&fecha_fin=YYYY-MM-DD`
- `GET/POST /api/reservas/`
- `GET/PATCH/DELETE /api/reservas/<id>/`
- `POST /api/reservas/<id>/check-in/`
- `POST /api/reservas/<id>/check-out/`
- `GET /api/reservas/<id>/contrato.pdf`

## Reglas implementadas

- Una reserva solo se crea si el vehiculo esta disponible y no existe solapamiento de fechas.
- El total se calcula como `dias * tarifa_diaria`.
- El check-in cambia la reserva a `en_alquiler`.
- El check-out cambia la reserva a `devuelta`.
- El contrato PDF se genera dinamicamente desde los datos de la reserva.
