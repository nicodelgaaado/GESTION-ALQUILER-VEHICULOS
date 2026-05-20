from django.db import migrations
from django.contrib.auth.hashers import make_password


def crear_admin(apps, schema_editor):
    CustomUser = apps.get_model('usuarios', 'CustomUser')
    if not CustomUser.objects.filter(username='admin@fleetflow.com').exists():
        CustomUser.objects.create(
            username='admin@fleetflow.com',
            email='admin@fleetflow.com',
            password=make_password('admin'),
            role='admin',
            is_staff=True,
            is_superuser=True,
            is_active=True,
            first_name='Admin',
            last_name='FleetFlow',
        )


def eliminar_admin(apps, schema_editor):
    CustomUser = apps.get_model('usuarios', 'CustomUser')
    CustomUser.objects.filter(username='admin@fleetflow.com').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(crear_admin, eliminar_admin),
    ]
