from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'role')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            'username': "Nom d'utilisateur",
            'first_name': 'Prénom',
            'last_name': 'Nom',
            'email': 'Adresse email',
            'password1': 'Mot de passe',
            'password2': 'Confirmer le mot de passe',
        }
        for field_name, placeholder in placeholders.items():
            if field_name in self.fields:
                self.fields[field_name].widget.attrs['placeholder'] = placeholder
                self.fields[field_name].label = ''
        if 'role' in self.fields:
            self.fields['role'].label = ''
            self.fields['role'].choices = [('', '-- Rôle --')] + [
                c for c in self.fields['role'].choices if c[0] != ''
            ]


class CustomUserChangeForm(UserChangeForm):
    password = None

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'role', 'is_active')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            'username': "Nom d'utilisateur",
            'first_name': 'Prénom',
            'last_name': 'Nom',
            'email': 'Adresse email',
        }
        for field_name, placeholder in placeholders.items():
            if field_name in self.fields:
                self.fields[field_name].widget.attrs['placeholder'] = placeholder
                self.fields[field_name].label = ''
        if 'role' in self.fields:
            self.fields['role'].label = ''
            self.fields['role'].choices = [('', '-- Rôle --')] + [
                c for c in self.fields['role'].choices if c[0] != ''
            ]
        if 'is_active' in self.fields:
            self.fields['is_active'].label = 'Actif'


class LoginForm(forms.Form):
    username = forms.CharField(max_length=150, label='',
        widget=forms.TextInput(attrs={'placeholder': "Nom d'utilisateur"}))
    password = forms.CharField(label='',
        widget=forms.PasswordInput(attrs={'placeholder': 'Mot de passe'}))
