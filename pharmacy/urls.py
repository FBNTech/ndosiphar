from django.urls import path
from . import views
from . import excel_views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    # Taux
    path('taux/', views.taux_list, name='taux_list'),
    path('taux/nouveau/', views.taux_create, name='taux_create'),
    path('taux/<int:pk>/modifier/', views.taux_edit, name='taux_edit'),
    path('taux/<int:pk>/supprimer/', views.taux_delete, name='taux_delete'),

    # Fournisseurs
    path('fournisseurs/', views.fournisseur_list, name='fournisseur_list'),
    path('fournisseurs/nouveau/', views.fournisseur_create, name='fournisseur_create'),
    path('fournisseurs/<int:pk>/modifier/', views.fournisseur_edit, name='fournisseur_edit'),
    path('fournisseurs/<int:pk>/supprimer/', views.fournisseur_delete, name='fournisseur_delete'),

    # Produits
    path('produits/', views.produit_list, name='produit_list'),
    path('produits/liste-pdf/', views.produits_liste_pdf, name='produits_liste_pdf'),
    path('produits/reset-fournisseur/', views.produit_reset_fournisseur, name='produit_reset_fournisseur'),
    path('produits/<int:pk>/', views.produit_detail, name='produit_detail'),
    path('produits/<int:pk>/modifier/', views.produit_edit, name='produit_edit'),
    path('produits/<int:pk>/ajouter-stock/', views.produit_ajouter_stock, name='produit_ajouter_stock'),
    path('produits/<int:pk>/supprimer/', views.produit_delete, name='produit_delete'),

    # Clients
    path('clients/', views.client_list, name='client_list'),
    path('clients/nouveau/', views.client_create, name='client_create'),
    path('clients/<int:pk>/modifier/', views.client_edit, name='client_edit'),
    path('clients/<int:pk>/supprimer/', views.client_delete, name='client_delete'),

    # API
    path('api/produit/<int:pk>/', views.api_produit_info, name='api_produit_info'),

    # Ventes
    path('ventes/', views.vente_home, name='vente_home'),
    path('ventes/liste/', views.vente_list, name='vente_list'),
    path('ventes/nouveau/', views.vente_create, name='vente_create'),
    path('ventes/credits/', views.vente_credit_list, name='vente_credit_list'),
    path('ventes/<int:pk>/payer/', views.vente_credit_payer, name='vente_credit_payer'),
    path('ventes/<int:pk>/modifier/', views.vente_edit, name='vente_edit'),
    path('ventes/<int:pk>/', views.vente_detail, name='vente_detail'),
    path('ventes/<int:pk>/ajouter-ligne/', views.vente_add_ligne, name='vente_add_ligne'),
    path('ventes/<int:pk>/supprimer-ligne/<int:ligne_pk>/', views.vente_remove_ligne, name='vente_remove_ligne'),
    path('ventes/<int:pk>/supprimer/', views.vente_delete, name='vente_delete'),
    path('ventes/<int:pk>/facture/', views.facture_pdf, name='facture_pdf'),
    path('ventes/rapport-journalier/', views.rapport_journalier_pdf, name='rapport_journalier'),
    
    # Analyse
    path('analyse-clients/', views.analyse_clients, name='analyse_clients'),

    # Export/Import Excel (admin)
    path('fournisseurs/export/', excel_views.export_fournisseurs, name='export_fournisseurs'),
    path('fournisseurs/import/', excel_views.import_fournisseurs, name='import_fournisseurs'),
    path('produits/export/', excel_views.export_produits, name='export_produits'),
    path('produits/import/', excel_views.import_produits, name='import_produits'),
    path('clients/export/', excel_views.export_clients, name='export_clients'),
    path('clients/import/', excel_views.import_clients, name='import_clients'),
    path('ventes/export/', excel_views.export_ventes, name='export_ventes'),

    # Inventaire
    path('inventaires/', views.inventaire_list, name='inventaire_list'),
    path('inventaires/mes-comptages/', views.inventaire_mes_comptages, name='inventaire_mes_comptages'),
    path('inventaires/nouveau/', views.inventaire_create, name='inventaire_create'),
    path('inventaires/<int:pk>/saisie/', views.inventaire_saisie, name='inventaire_saisie'),
    path('inventaires/<int:pk>/ligne/<int:ligne_pk>/compter/', views.inventaire_ligne_compter, name='inventaire_ligne_compter'),
    path('inventaires/<int:pk>/valider/', views.inventaire_valider, name='inventaire_valider'),
    path('inventaires/<int:pk>/', views.inventaire_detail, name='inventaire_detail'),
    path('inventaires/<int:pk>/annuler/', views.inventaire_annuler, name='inventaire_annuler'),
    path('inventaires/<int:pk>/supprimer/', views.inventaire_delete, name='inventaire_delete'),
    path('inventaires/<int:pk>/pdf/', views.inventaire_pdf, name='inventaire_pdf'),
    # Historique
    path('historique-ventes/', views.historique_ventes, name='historique_ventes'),
    path('historique/', views.historique_list, name='historique_list'),
]
