from django.urls import path
from . import views
from . import excel_views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    # Catégories
    path('categories/', views.categorie_list, name='categorie_list'),
    path('categories/nouveau/', views.categorie_create, name='categorie_create'),
    path('categories/<int:pk>/modifier/', views.categorie_edit, name='categorie_edit'),
    path('categories/<int:pk>/supprimer/', views.categorie_delete, name='categorie_delete'),

    # Fournisseurs
    path('fournisseurs/', views.fournisseur_list, name='fournisseur_list'),
    path('fournisseurs/nouveau/', views.fournisseur_create, name='fournisseur_create'),
    path('fournisseurs/<int:pk>/modifier/', views.fournisseur_edit, name='fournisseur_edit'),
    path('fournisseurs/<int:pk>/supprimer/', views.fournisseur_delete, name='fournisseur_delete'),

    # Produits
    path('produits/', views.produit_list, name='produit_list'),
    path('produits/nouveau/', views.produit_create, name='produit_create'),
    path('produits/<int:pk>/modifier/', views.produit_edit, name='produit_edit'),
    path('produits/<int:pk>/supprimer/', views.produit_delete, name='produit_delete'),

    # Clients
    path('clients/', views.client_list, name='client_list'),
    path('clients/nouveau/', views.client_create, name='client_create'),
    path('clients/<int:pk>/modifier/', views.client_edit, name='client_edit'),
    path('clients/<int:pk>/supprimer/', views.client_delete, name='client_delete'),

    # API
    path('api/produit/<int:pk>/', views.api_produit_info, name='api_produit_info'),

    # Ventes
    path('ventes/', views.vente_list, name='vente_list'),
    path('ventes/nouveau/', views.vente_create, name='vente_create'),
    path('ventes/<int:pk>/', views.vente_detail, name='vente_detail'),
    path('ventes/<int:pk>/ajouter-ligne/', views.vente_add_ligne, name='vente_add_ligne'),
    path('ventes/<int:pk>/supprimer-ligne/<int:ligne_pk>/', views.vente_remove_ligne, name='vente_remove_ligne'),
    path('ventes/<int:pk>/supprimer/', views.vente_delete, name='vente_delete'),
    path('ventes/<int:pk>/facture/', views.facture_pdf, name='facture_pdf'),

    # Export/Import Excel (admin)
    path('categories/export/', excel_views.export_categories, name='export_categories'),
    path('categories/import/', excel_views.import_categories, name='import_categories'),
    path('fournisseurs/export/', excel_views.export_fournisseurs, name='export_fournisseurs'),
    path('fournisseurs/import/', excel_views.import_fournisseurs, name='import_fournisseurs'),
    path('produits/export/', excel_views.export_produits, name='export_produits'),
    path('produits/import/', excel_views.import_produits, name='import_produits'),
    path('clients/export/', excel_views.export_clients, name='export_clients'),
    path('clients/import/', excel_views.import_clients, name='import_clients'),
    path('ventes/export/', excel_views.export_ventes, name='export_ventes'),

    # Historique (admin)
    path('historique/', views.historique_list, name='historique_list'),
]
