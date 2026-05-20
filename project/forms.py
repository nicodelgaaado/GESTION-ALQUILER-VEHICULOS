from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from vehiculo.models import Vehiculo, Categoria, Tarifa
from reservas.models import Reserva


class FleetFlowAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="Correo",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control form-control-lg app-input",
                "placeholder": "ops@fleetflow.ai",
                "autocomplete": "email",
            }
        ),
    )
    password = forms.CharField(
        label="Contrasena",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control form-control-lg app-input",
                "placeholder": "********",
                "autocomplete": "current-password",
            }
        ),
    )


class FleetFlowRegistrationForm(UserCreationForm):
    full_name = forms.CharField(
        label="Nombre completo",
        max_length=150,
        widget=forms.TextInput(
            attrs={"class": "form-control app-input", "placeholder": "Laura Mendoza"}
        ),
    )
    company = forms.CharField(
        label="Empresa",
        max_length=150,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control app-input", "placeholder": "Aurora Rentals"}
        ),
    )
    username = forms.EmailField(
        label="Correo",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control app-input",
                "placeholder": "hello@aurorarentals.com",
                "autocomplete": "email",
            }
        ),
    )
    role = forms.ChoiceField(
        label="Rol",
        choices=[
            ("cliente", "Cliente"),
            ("admin", "Administrador"),
        ],
        widget=forms.Select(attrs={"class": "form-select app-input"}),
    )
    password1 = forms.CharField(
        label="Contrasena",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control app-input",
                "placeholder": "Crea una contrasena",
                "autocomplete": "new-password",
            }
        ),
    )
    password2 = forms.CharField(
        label="Confirmar contrasena",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control app-input",
                "placeholder": "Repite la contrasena",
                "autocomplete": "new-password",
            }
        ),
    )
    terms = forms.BooleanField(
        label="Acepto los terminos de la plataforma y la politica de procesamiento contractual.",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("full_name", "company", "username", "role", "password1", "password2", "terms")

    def clean_username(self):
        email = self.cleaned_data["username"].strip().lower()
        user_model = get_user_model()
        if user_model.objects.filter(username__iexact=email).exists():
            raise forms.ValidationError("Ya existe una cuenta con este correo.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        full_name = self.cleaned_data["full_name"].strip()
        name_parts = full_name.split(maxsplit=1)
        user.first_name = name_parts[0]
        user.last_name = name_parts[1] if len(name_parts) > 1 else ""
        user.empresa = self.cleaned_data["company"].strip()
        user.email = self.cleaned_data["username"]
        user.username = self.cleaned_data["username"]
        user.role = self.cleaned_data["role"]
        user.is_staff = user.role == "admin"
        if commit:
            user.save()
        return user


# ============================================================================
# Formularios ModelForm para el negocio (Vehículos, Categorías, Tarifas, Reservas)
# ============================================================================

class CategoriaForm(forms.ModelForm):
    """Formulario para crear/editar categorías de vehículos."""

    class Meta:
        model = Categoria
        fields = ['nombre', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: SUV, Sedan, Comercial',
                'required': True,
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Descripción de la categoría...',
                'rows': 3,
            }),
        }

    def clean_nombre(self):
        """Validar que el nombre sea único (case-insensitive)."""
        nombre = self.cleaned_data['nombre'].strip().title()
        existe = Categoria.objects.filter(nombre__iexact=nombre)
        if self.instance.pk:
            existe = existe.exclude(pk=self.instance.pk)
        if existe.exists():
            raise forms.ValidationError('Ya existe una categoría con este nombre.')
        return nombre


class TarifaForm(forms.ModelForm):
    """Formulario para crear/editar tarifas de alquiler."""

    class Meta:
        model = Tarifa
        fields = ['categoria', 'precio_diario', 'activa']
        widgets = {
            'categoria': forms.Select(attrs={
                'class': 'form-select',
                'required': True,
            }),
            'precio_diario': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 150.00',
                'step': '0.01',
                'min': '0',
                'required': True,
            }),
            'activa': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }

    def clean_precio_diario(self):
        """Validar que el precio sea positivo."""
        precio = self.cleaned_data['precio_diario']
        if precio <= 0:
            raise forms.ValidationError('El precio debe ser mayor a 0.')
        return precio


class VehiculoForm(forms.ModelForm):
    """Formulario para crear/editar vehículos."""

    class Meta:
        model = Vehiculo
        fields = ['placa', 'marca', 'modelo', 'anio', 'categoria', 'estado', 
                  'kilometraje', 'descripcion']
        widgets = {
            'placa': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: ABC-1234',
                'maxlength': '12',
                'required': True,
                'style': 'text-transform: uppercase;',
            }),
            'marca': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Toyota',
                'required': True,
            }),
            'modelo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Camry',
                'required': True,
            }),
            'anio': forms.NumberInput(attrs={
                'class': 'form-control',
                'type': 'number',
                'min': '1980',
                'placeholder': 'Ej: 2024',
                'required': True,
            }),
            'categoria': forms.Select(attrs={
                'class': 'form-select',
                'required': True,
            }),
            'estado': forms.Select(attrs={
                'class': 'form-select',
                'required': True,
            }),
            'kilometraje': forms.NumberInput(attrs={
                'class': 'form-control',
                'type': 'number',
                'min': '0',
                'placeholder': 'Km actuales del vehículo',
                'required': True,
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Características especiales, estado físico, etc...',
                'rows': 3,
            }),
        }

    def clean_placa(self):
        """Validar que la placa sea única y tenga formato válido."""
        placa = self.cleaned_data['placa'].strip().upper()
        existe = Vehiculo.objects.filter(placa__iexact=placa)
        if self.instance.pk:
            existe = existe.exclude(pk=self.instance.pk)
        if existe.exists():
            raise forms.ValidationError('Ya existe un vehículo con esta placa.')
        return placa

    def clean_anio(self):
        """Validar que el año sea razonable."""
        from datetime import datetime
        anio = self.cleaned_data['anio']
        año_actual = datetime.now().year
        if anio > año_actual:
            raise forms.ValidationError(f'El año no puede ser mayor al año actual ({año_actual}).')
        if anio < 1980:
            raise forms.ValidationError('El año debe ser 1980 o posterior.')
        return anio

    def clean_marca(self):
        """Normalizar marca a formato título."""
        return self.cleaned_data['marca'].strip().title()

    def clean_modelo(self):
        """Normalizar modelo a formato título."""
        return self.cleaned_data['modelo'].strip().title()


class ReservaForm(forms.ModelForm):
    """Formulario administrativo para crear/editar reservas."""

    class Meta:
        model = Reserva
        fields = ['usuario', 'vehiculo', 'fecha_inicio', 'fecha_fin', 'estado']
        widgets = {
            'usuario': forms.Select(attrs={
                'class': 'form-select',
                'required': True,
            }),
            'vehiculo': forms.Select(attrs={
                'class': 'form-select',
                'required': True,
            }),
            'fecha_inicio': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True,
            }),
            'fecha_fin': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True,
            }),
            'estado': forms.Select(attrs={
                'class': 'form-select',
                'required': True,
            }),
        }

    TRANSICIONES_PERMITIDAS = {
        Reserva.PENDIENTE: {Reserva.PENDIENTE, Reserva.CONFIRMADA, Reserva.CANCELADA},
        Reserva.CONFIRMADA: {Reserva.CONFIRMADA, Reserva.CANCELADA},
        Reserva.EN_ALQUILER: {Reserva.EN_ALQUILER},
        Reserva.DEVUELTA: {Reserva.DEVUELTA},
        Reserva.CANCELADA: {Reserva.CANCELADA},
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user_model = get_user_model()
        self.fields["usuario"].queryset = user_model.objects.order_by("username")
        self.fields["vehiculo"].queryset = Vehiculo.objects.select_related("categoria").order_by(
            "marca", "modelo", "placa"
        )

        if not self.instance.pk:
            self.fields["estado"].choices = [
                (Reserva.PENDIENTE, "Pendiente"),
                (Reserva.CONFIRMADA, "Confirmada"),
            ]

    def clean(self):
        """Validación completa del formulario incluyendo solapamiento."""
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')
        vehiculo = cleaned_data.get('vehiculo')
        estado = cleaned_data.get('estado') or Reserva.PENDIENTE

        if fecha_inicio and fecha_fin:
            if fecha_fin <= fecha_inicio:
                self.add_error('fecha_fin', 
                    'La fecha de fin debe ser posterior a la fecha de inicio.')

        if self.instance.pk and estado != self.instance.estado:
            permitidos = self.TRANSICIONES_PERMITIDAS.get(self.instance.estado, {self.instance.estado})
            if estado not in permitidos:
                self.add_error(
                    'estado',
                    'Use las acciones de check-in/check-out o cancelación para cambiar este estado.',
                )

        if vehiculo and estado in Reserva.ESTADOS_ACTIVOS and vehiculo.estado != Vehiculo.DISPONIBLE:
            self.add_error('vehiculo', 'Solo se pueden reservar vehiculos en estado disponible.')

        if vehiculo and fecha_inicio and fecha_fin and estado in Reserva.ESTADOS_ACTIVOS:
            disponible = Reserva.vehiculo_disponible(
                vehiculo,
                fecha_inicio,
                fecha_fin,
                excluir_reserva=self.instance.pk if self.instance.pk else None
            )
            if not disponible:
                self.add_error('vehiculo',
                    'Este vehículo no está disponible para las fechas seleccionadas.')

        return cleaned_data


class ReservaFormCliente(forms.ModelForm):
    """Formulario simplificado para clientes (sin estado)."""

    class Meta:
        model = Reserva
        fields = ['vehiculo', 'fecha_inicio', 'fecha_fin']
        widgets = {
            'vehiculo': forms.Select(attrs={
                'class': 'form-select',
                'required': True,
            }),
            'fecha_inicio': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True,
            }),
            'fecha_fin': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["vehiculo"].queryset = Vehiculo.objects.filter(
            estado=Vehiculo.DISPONIBLE
        ).select_related("categoria")

    def clean_vehiculo(self):
        vehiculo = self.cleaned_data.get("vehiculo")
        if not vehiculo:
            return vehiculo
        if vehiculo.estado != Vehiculo.DISPONIBLE:
            raise forms.ValidationError("Solo se pueden reservar vehiculos disponibles.")
        return vehiculo

    def clean(self):
        """Validación completa incluyendo solapamiento."""
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')
        vehiculo = cleaned_data.get('vehiculo')

        # Validar fechas
        if fecha_inicio and fecha_fin:
            if fecha_fin <= fecha_inicio:
                self.add_error('fecha_fin',
                    'La fecha de fin debe ser posterior a la fecha de inicio.')

        # Validar disponibilidad (solapamiento)
        if vehiculo and fecha_inicio and fecha_fin:
            disponible = Reserva.vehiculo_disponible(
                vehiculo,
                fecha_inicio,
                fecha_fin,
                excluir_reserva=self.instance.pk if self.instance.pk else None
            )
            if not disponible:
                self.add_error('vehiculo',
                    'Este vehículo no está disponible para las fechas seleccionadas.')

        return cleaned_data
