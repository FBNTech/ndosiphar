from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Administrateur'),
        ('vendeur', 'Vendeur'),
        ('gestionnaire', 'Gestionnaire'),
        ('controleur', 'Contrôleur'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='vendeur', verbose_name="Rôle")

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_vendeur(self):
        return self.role == 'vendeur'

    @property
    def is_gestionnaire(self):
        return self.role == 'gestionnaire'

    @property
    def is_controleur(self):
        return self.role == 'controleur'
