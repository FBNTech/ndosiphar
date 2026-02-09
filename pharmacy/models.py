from django.db import models
from django.conf import settings
from decimal import Decimal
from datetime import date


class Categorie(models.Model):
    code_categorie = models.AutoField(primary_key=True, verbose_name="Code Catégorie")
    designation = models.CharField(max_length=200, verbose_name="Désignation Catégorie")

    class Meta:
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"
        ordering = ['designation']

    def __str__(self):
        return self.designation


class Fournisseur(models.Model):
    code_fournisseur = models.AutoField(primary_key=True, verbose_name="Code Fournisseur")
    designation = models.CharField(max_length=200, verbose_name="Désignation Fournisseur")
    marge_beneficiaire = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Marge Bénéficiaire (%)")

    class Meta:
        verbose_name = "Fournisseur"
        verbose_name_plural = "Fournisseurs"
        ordering = ['designation']

    def __str__(self):
        return f"{self.designation} ({self.marge_beneficiaire}%)"


class Produit(models.Model):
    code_produit = models.AutoField(primary_key=True, verbose_name="Code Produit")
    designation = models.CharField(max_length=200, verbose_name="Désignation Produit")
    prix_achat = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Prix d'Achat (FC)")
    quantite_initiale = models.IntegerField(default=0, verbose_name="Quantité Initiale")
    quantite_stock = models.IntegerField(default=0, verbose_name="Quantité en Stock")
    quantite_alerte = models.IntegerField(default=10, verbose_name="Quantité Alerte")
    jours_alerte_expiration = models.IntegerField(default=30, verbose_name="Alerte Expiration (jours avant)")
    fournisseur = models.ForeignKey(Fournisseur, on_delete=models.PROTECT, verbose_name="Fournisseur")
    date_expiration = models.DateField(verbose_name="Date d'Expiration")
    categorie = models.ForeignKey(Categorie, on_delete=models.PROTECT, verbose_name="Catégorie")

    class Meta:
        verbose_name = "Produit"
        verbose_name_plural = "Produits"
        ordering = ['designation']

    def __str__(self):
        return self.designation

    @property
    def prix_vente(self):
        marge = self.fournisseur.marge_beneficiaire
        return self.prix_achat + (self.prix_achat * marge / Decimal('100'))

    @property
    def stock_alerte(self):
        return self.quantite_stock <= self.quantite_alerte

    @property
    def expiration_alerte(self):
        if self.date_expiration:
            jours_restants = (self.date_expiration - date.today()).days
            return jours_restants <= self.jours_alerte_expiration
        return False

    @property
    def jours_avant_expiration(self):
        if self.date_expiration:
            return (self.date_expiration - date.today()).days
        return None

    @property
    def est_expire(self):
        if self.date_expiration:
            return self.date_expiration <= date.today()
        return False


class Client(models.Model):
    code_client = models.AutoField(primary_key=True, verbose_name="Code Client")
    nom = models.CharField(max_length=200, verbose_name="Nom du Client")
    telephone = models.CharField(max_length=20, blank=True, verbose_name="Téléphone")
    adresse = models.CharField(max_length=300, blank=True, verbose_name="Adresse")

    class Meta:
        verbose_name = "Client"
        verbose_name_plural = "Clients"
        ordering = ['nom']

    def __str__(self):
        return self.nom


class Vente(models.Model):
    TYPE_CHOICES = (
        ('detail', 'Détail'),
        ('gros', 'Gros'),
    )
    code_vente = models.AutoField(primary_key=True, verbose_name="Code Vente")
    date_vente = models.DateTimeField(auto_now_add=True, verbose_name="Date de Vente")
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Client")
    type_vente = models.CharField(max_length=10, choices=TYPE_CHOICES, default='detail', verbose_name="Type de Vente")
    montant_total = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Montant Total (FC)")
    remise_pourcent = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Remise (%)")
    montant_remise = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Montant Remise (FC)")
    montant_net = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Montant Net (FC)")
    observation = models.TextField(blank=True, verbose_name="Observation")
    vendeur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name="Vendeur")

    class Meta:
        verbose_name = "Vente"
        verbose_name_plural = "Ventes"
        ordering = ['-date_vente']

    def __str__(self):
        return f"Vente #{self.code_vente} - {self.date_vente.strftime('%d/%m/%Y %H:%M')}"

    def calculer_total(self):
        total = sum(ligne.montant_ligne for ligne in self.lignes.all())
        self.montant_total = total
        if total > Decimal('10000'):
            self.remise_pourcent = Decimal('10')
            self.montant_remise = total * Decimal('10') / Decimal('100')
        else:
            self.remise_pourcent = Decimal('0')
            self.montant_remise = Decimal('0')
        self.montant_net = total - self.montant_remise
        self.save()
        return self.montant_net


class LigneVente(models.Model):
    vente = models.ForeignKey(Vente, on_delete=models.CASCADE, related_name='lignes', verbose_name="Vente")
    produit = models.ForeignKey(Produit, on_delete=models.PROTECT, verbose_name="Produit")
    quantite = models.PositiveIntegerField(verbose_name="Quantité Vendue")
    prix_unitaire = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Prix Unitaire (FC)")
    montant_ligne = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Montant Ligne (FC)")

    class Meta:
        verbose_name = "Ligne de Vente"
        verbose_name_plural = "Lignes de Vente"

    def __str__(self):
        return f"{self.produit.designation} x {self.quantite}"

    def save(self, *args, **kwargs):
        self.montant_ligne = self.quantite * self.prix_unitaire
        super().save(*args, **kwargs)


class Historique(models.Model):
    ACTION_CHOICES = (
        ('creation', 'Création'),
        ('modification', 'Modification'),
        ('suppression', 'Suppression'),
        ('connexion', 'Connexion'),
    )
    date_action = models.DateTimeField(auto_now_add=True, verbose_name="Date")
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name="Utilisateur")
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name="Action")
    modele = models.CharField(max_length=100, verbose_name="Modèle", blank=True)
    detail = models.TextField(verbose_name="Détail", blank=True)

    class Meta:
        verbose_name = "Historique"
        verbose_name_plural = "Historiques"
        ordering = ['-date_action']

    def __str__(self):
        return f"{self.date_action:%d/%m/%Y %H:%M} - {self.utilisateur} - {self.get_action_display()}"
