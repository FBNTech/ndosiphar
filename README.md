# NDOSIPHAR - Système de Gestion de Pharmacie

Application web de gestion pharmaceutique - Vente en Gros et au Détail.

## Stack Technique
- **Backend** : Django 6.0.2
- **Frontend** : Bootstrap 5, Inter Font, Bootstrap Icons
- **PDF** : xhtml2pdf
- **Excel** : openpyxl
- **Base de données** : SQLite

## Installation locale

```bash
git clone https://github.com/FBNTech/ndosiphar.git
cd ndosiphar
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 8000
```

## Rôles utilisateurs
| Rôle | Accès |
|------|-------|
| **Administrateur** | Tout + Utilisateurs + Historique |
| **Vendeur** | Clients, Ventes |
| **Gestionnaire** | Catégories, Fournisseurs, Produits |
| **Contrôleur** | Tout sauf Historique et Utilisateurs |

## Fonctionnalités
- Gestion des catégories, fournisseurs, produits, clients
- Ventes avec calcul automatique et remise 10% au-delà de 10 000 FC
- Facture PDF (A4 paysage, 2 exemplaires A5)
- Export/Import Excel (admin)
- Tableau de bord avec alertes stock et expiration
- Historique d'audit (admin)
