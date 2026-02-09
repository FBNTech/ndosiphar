from django.contrib import admin
from .models import Categorie, Fournisseur, Produit, Client, Vente, LigneVente


@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display = ('code_categorie', 'designation')
    search_fields = ('designation',)


@admin.register(Fournisseur)
class FournisseurAdmin(admin.ModelAdmin):
    list_display = ('code_fournisseur', 'designation', 'marge_beneficiaire')
    search_fields = ('designation',)


@admin.register(Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display = ('code_produit', 'designation', 'prix_achat', 'prix_vente', 'quantite_stock', 'categorie', 'fournisseur')
    list_filter = ('categorie', 'fournisseur')
    search_fields = ('designation',)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('code_client', 'nom', 'telephone', 'adresse')
    search_fields = ('nom',)


class LigneVenteInline(admin.TabularInline):
    model = LigneVente
    extra = 0


@admin.register(Vente)
class VenteAdmin(admin.ModelAdmin):
    list_display = ('code_vente', 'date_vente', 'client', 'type_vente', 'montant_total', 'vendeur')
    list_filter = ('type_vente', 'date_vente')
    inlines = [LigneVenteInline]
