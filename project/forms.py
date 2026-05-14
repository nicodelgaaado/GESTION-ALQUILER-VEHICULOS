from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm


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
            ("administrador", "Administrador"),
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
        user.email = self.cleaned_data["username"]
        user.username = self.cleaned_data["username"]
        user.is_staff = self.cleaned_data["role"] == "administrador"
        if commit:
            user.save()
        return user
