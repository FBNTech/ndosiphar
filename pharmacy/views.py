from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden
from functools import wraps
from django.template.loader import get_template
from django.utils import timezone
from xhtml2pdf import pisa
from io import BytesIO
from django.db import models
from datetime import date, timedelta
from decimal import Decimal
import json
from .models import Taux, Fournisseur, Produit, Client, Vente, LigneVente, Historique, Inventaire, LigneInventaire
from django.conf import settings
from .forms import (TauxForm, FournisseurForm, ProduitForm,
                    ClientForm, VenteForm, VenteCompletForm, LigneVenteForm)


def non_vendeur_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.is_vendeur:
            messages.error(request, "Vous n'avez pas la permission d'effectuer cette action.")
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_gestionnaire_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not (request.user.is_admin or request.user.is_gestionnaire):
            messages.error(request, "Accès réservé à l'administrateur et au gestionnaire.")
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def is_admin_or_gerant(user):
    return user.is_admin or getattr(user, 'is_gerant', False)


def admin_gerant_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not is_admin_or_gerant(request.user):
            messages.error(request, "Accès réservé à l'administrateur et au gérant.")
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def can_count_inventory(user, inventaire):
    if is_admin_or_gerant(user):
        return True
    if user.role not in ('vendeur', 'gestionnaire', 'controleur'):
        return False
    return inventaire.compteurs_autorises.filter(pk=user.pk).exists()


@login_required
def dashboard(request):
    aujourd_hui = date.today()
    debut_semaine = aujourd_hui - timedelta(days=aujourd_hui.weekday())
    debut_mois = aujourd_hui.replace(day=1)

    ventes_jour = Vente.objects.filter(date_vente__date=aujourd_hui).aggregate(
        total=models.Sum('montant_total'), nombre=models.Count('pk'))
    ventes_semaine = Vente.objects.filter(date_vente__date__gte=debut_semaine).aggregate(
        total=models.Sum('montant_total'), nombre=models.Count('pk'))
    ventes_mois = Vente.objects.filter(date_vente__date__gte=debut_mois).aggregate(
        total=models.Sum('montant_total'), nombre=models.Count('pk'))

    # Vérifier si le vendeur doit confirmer le taux de change
    afficher_modal_taux = False
    taux_usd = None
    try:
        taux_usd = Taux.objects.get(code_devise='USD')
    except Taux.DoesNotExist:
        pass
    
    if request.user.is_vendeur and not request.session.get('taux_confirme_aujourd_hui') == str(aujourd_hui):
        afficher_modal_taux = True
    
    # Si le vendeur confirme/modifie le taux via POST
    if request.method == 'POST' and 'confirmer_taux' in request.POST:
        nouveau_taux = request.POST.get('montant_fc')
        if nouveau_taux:
            try:
                nouveau_taux = float(nouveau_taux.replace(',', '.'))
                if taux_usd:
                    taux_usd.montant_fc = nouveau_taux
                    taux_usd.save()
                else:
                    taux_usd = Taux.objects.create(code_devise='USD', montant_fc=nouveau_taux)
                Historique.objects.create(
                    utilisateur=request.user,
                    action='modification_taux',
                    modele='Taux',
                    detail=f"Taux USD mis à jour à {nouveau_taux} FC par {request.user.username}"
                )
                request.session['taux_confirme_aujourd_hui'] = str(aujourd_hui)
                messages.success(request, f"Taux de change mis à jour : 1 USD = {nouveau_taux} FC")
            except (ValueError, TypeError):
                messages.error(request, "Valeur de taux invalide.")
        else:
            request.session['taux_confirme_aujourd_hui'] = str(aujourd_hui)
            messages.info(request, "Taux de change confirmé.")
        return redirect('dashboard')

    context = {
        'total_produits': Produit.objects.count(),
        'total_fournisseurs': Fournisseur.objects.count(),
        'total_clients': Client.objects.count(),
        'total_ventes': Vente.objects.count(),
        'total_taux': Taux.objects.count(),
        'dernier_taux': taux_usd or Taux.objects.first(),
        'ventes_jour': ventes_jour['total'] or 0,
        'ventes_jour_nombre': ventes_jour['nombre'],
        'ventes_semaine': ventes_semaine['total'] or 0,
        'ventes_semaine_nombre': ventes_semaine['nombre'],
        'ventes_mois': ventes_mois['total'] or 0,
        'ventes_mois_nombre': ventes_mois['nombre'],
        'produits_alerte': Produit.objects.filter(quantite_stock__lte=models.F('quantite_alerte')),
        'nb_requisition': Produit.objects.filter(quantite_stock__lte=models.F('quantite_alerte')).count(),
        'produits_expiration': Produit.objects.filter(
            date_expiration__lte=date.today() + timedelta(days=30)
        ).order_by('date_expiration'),
        'ventes_recentes': Vente.objects.all()[:5],
        'produits_recents': Produit.objects.select_related('fournisseur').order_by('-date_creation', '-code_produit')[:10],
        'afficher_modal_taux': afficher_modal_taux,
        'taux_usd': taux_usd,
    }
    return render(request, 'pharmacy/dashboard.html', context)




# ============ TAUX CRUD ============

@login_required
def taux_list(request):
    taux = Taux.objects.all()
    return render(request, 'pharmacy/taux_list.html', {'taux': taux})


@non_vendeur_required
def taux_create(request):
    if request.method == 'POST':
        form = TauxForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Taux créé avec succès.")
            return redirect('taux_list')
    else:
        form = TauxForm()
    return render(request, 'pharmacy/taux_form.html', {'form': form, 'title': 'Nouveau Taux'})


@login_required
def taux_edit(request, pk):
    taux = get_object_or_404(Taux, pk=pk)
    if request.method == 'POST':
        form = TauxForm(request.POST, instance=taux)
        if form.is_valid():
            form.save()
            Historique.objects.create(
                utilisateur=request.user,
                action='modification_taux',
                modele='Taux',
                detail=f"Taux {taux.code_devise} modifié à {taux.montant_fc} FC par {request.user.username}"
            )
            messages.success(request, "Taux modifié avec succès.")
            return redirect('taux_list')
    else:
        form = TauxForm(instance=taux)
    return render(request, 'pharmacy/taux_form.html', {'form': form, 'title': 'Modifier Taux'})


@non_vendeur_required
def taux_delete(request, pk):
    taux = get_object_or_404(Taux, pk=pk)
    if request.method == 'POST':
        try:
            taux.delete()
            messages.success(request, "Taux supprimé avec succès.")
        except Exception:
            messages.error(request, "Impossible de supprimer ce taux.")
        return redirect('taux_list')
    return render(request, 'pharmacy/confirm_delete.html', {'object': taux, 'type': 'Taux'})


# ============ FOURNISSEUR CRUD ============

@login_required
def fournisseur_list(request):
    fournisseurs = Fournisseur.objects.all()
    return render(request, 'pharmacy/fournisseur_list.html', {'fournisseurs': fournisseurs})


@non_vendeur_required
def fournisseur_create(request):
    if request.method == 'POST':
        form = FournisseurForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Fournisseur créé avec succès.")
            return redirect('fournisseur_list')
    else:
        form = FournisseurForm()
    return render(request, 'pharmacy/fournisseur_form.html', {'form': form, 'title': 'Nouveau Fournisseur'})


@non_vendeur_required
def fournisseur_edit(request, pk):
    fournisseur = get_object_or_404(Fournisseur, pk=pk)
    if request.method == 'POST':
        form = FournisseurForm(request.POST, instance=fournisseur)
        if form.is_valid():
            fournisseur = form.save()
            fournisseur.recalculer_prix_produits()
            messages.success(request, "Fournisseur modifié et prix des produits recalculés avec succès.")
            return redirect('fournisseur_list')
    else:
        form = FournisseurForm(instance=fournisseur)
    return render(request, 'pharmacy/fournisseur_form.html', {'form': form, 'title': 'Modifier Fournisseur'})


@non_vendeur_required
def fournisseur_delete(request, pk):
    fournisseur = get_object_or_404(Fournisseur, pk=pk)
    if request.method == 'POST':
        try:
            fournisseur.delete()
            messages.success(request, "Fournisseur supprimé avec succès.")
        except Exception:
            messages.error(request, "Impossible de supprimer ce fournisseur (utilisé par des produits).")
        return redirect('fournisseur_list')
    return render(request, 'pharmacy/confirm_delete.html', {'object': fournisseur, 'type': 'Fournisseur'})


# ============ PRODUIT CRUD ============

@non_vendeur_required
def produit_list(request):
    produits = Produit.objects.select_related('fournisseur').all().order_by('designation')
    
    # Gérer la soumission du formulaire de saisie rapide
    if request.method == 'POST':
        form = ProduitForm(request.POST)
        if form.is_valid():
            # Sauvegarder le fournisseur sélectionné en session
            fournisseur_id = request.POST.get('fournisseur')
            if fournisseur_id:
                request.session['fournisseur_selectionne_id'] = fournisseur_id
                try:
                    fournisseur = Fournisseur.objects.get(pk=fournisseur_id)
                    request.session['fournisseur_selectionne_nom'] = fournisseur.designation
                except Fournisseur.DoesNotExist:
                    pass
            
            produit = form.save()
            produit.calculer_prix_vente_usd()
            produit.save()
            messages.success(request, "Produit créé avec succès.")
            return redirect('produit_list')
    else:
        # Préparer le formulaire de saisie rapide
        form = ProduitForm()
        
        # Valeurs par défaut
        form.fields['quantite_alerte'].initial = 5
        form.fields['jours_alerte_expiration'].initial = 45
        
        # Pré-remplir le fournisseur si en session
        if 'fournisseur_selectionne_id' in request.session:
            try:
                fournisseur_id = request.session['fournisseur_selectionne_id']
                fournisseur = Fournisseur.objects.get(pk=fournisseur_id)
                form.fields['fournisseur'].initial = fournisseur
            except Fournisseur.DoesNotExist:
                # Nettoyer la session si le fournisseur n'existe plus
                del request.session['fournisseur_selectionne_id']
                if 'fournisseur_selectionne_nom' in request.session:
                    del request.session['fournisseur_selectionne_nom']
    
    # Préparer données fournisseurs pour le calcul JS du prix de vente
    import json
    fournisseurs_data = {}
    for f in Fournisseur.objects.all():
        fournisseurs_data[str(f.pk)] = float(f.marge_beneficiaire)
    
    # Taux USD
    taux_usd = 0
    try:
        taux_usd = float(Taux.objects.get(code_devise='USD').montant_fc)
    except Taux.DoesNotExist:
        pass
    
    # Statistiques produits par fournisseur
    total_produits = produits.count()
    produits_phatkin = produits.filter(fournisseur__designation__icontains='phatkin').count()
    produits_autres = total_produits - produits_phatkin
    stock_total = sum(p.quantite_stock for p in produits)
    produits_alerte = produits.filter(quantite_stock__lte=models.F('quantite_alerte')).count()
    
    stats_produits = {
        'total': total_produits,
        'phatkin': produits_phatkin,
        'autres': produits_autres,
        'stock_total': stock_total,
        'en_alerte': produits_alerte,
    }
    
    return render(request, 'pharmacy/produit_list.html', {
        'produits': produits,
        'form': form,
        'fournisseur_actuel': request.session.get('fournisseur_selectionne_nom'),
        'fournisseurs_marges_json': json.dumps(fournisseurs_data),
        'taux_usd': taux_usd,
        'stats': stats_produits,
    })


@non_vendeur_required
def produit_reset_fournisseur(request):
    """Vue pour réinitialiser le fournisseur sélectionné en session"""
    if request.method == 'POST':
        if 'fournisseur_selectionne_id' in request.session:
            del request.session['fournisseur_selectionne_id']
        if 'fournisseur_selectionne_nom' in request.session:
            del request.session['fournisseur_selectionne_nom']
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)


@non_vendeur_required
def produit_ajouter_stock(request, pk):
    """Ajouter une quantité au stock d'un produit existant (cumul)"""
    produit = get_object_or_404(Produit, pk=pk)
    if request.method == 'POST':
        try:
            quantite = int(request.POST.get('quantite', 0))
            if quantite > 0:
                produit.quantite_stock += quantite
                produit.quantite_initiale += quantite
                produit.save()
                Historique.objects.create(
                    utilisateur=request.user,
                    action='ajout_stock',
                    modele='Produit',
                    detail=f"Ajout de {quantite} unités au stock de {produit.designation} (nouveau stock: {produit.quantite_stock})"
                )
                messages.success(request, f"{quantite} unités ajoutées au stock de {produit.designation}. Nouveau stock: {produit.quantite_stock}")
            else:
                messages.error(request, "La quantité doit être supérieure à 0.")
        except (ValueError, TypeError):
            messages.error(request, "Quantité invalide.")
        return redirect('produit_list')
    return redirect('produit_list')


@non_vendeur_required
def produit_edit(request, pk):
    produit = get_object_or_404(Produit, pk=pk)
    if request.method == 'POST':
        form = ProduitForm(request.POST, instance=produit)
        if form.is_valid():
            produit = form.save()
            produit.calculer_prix_vente_usd()
            produit.save()
            messages.success(request, "Produit modifié avec succès.")
            return redirect('produit_list')
    else:
        form = ProduitForm(instance=produit)
    return render(request, 'pharmacy/produit_form.html', {'form': form, 'title': 'Modifier Produit'})


@non_vendeur_required
def produit_delete(request, pk):
    produit = get_object_or_404(Produit, pk=pk)
    if request.method == 'POST':
        try:
            produit.delete()
            messages.success(request, "Produit supprimé avec succès.")
        except Exception:
            messages.error(request, "Impossible de supprimer ce produit (utilisé dans des ventes).")
        return redirect('produit_list')
    return render(request, 'pharmacy/confirm_delete.html', {'object': produit, 'type': 'Produit'})


@admin_gestionnaire_required
def produit_detail(request, pk):
    produit = get_object_or_404(Produit.objects.select_related('fournisseur'), pk=pk)
    try:
        taux_usd = Taux.objects.get(code_devise='USD')
    except Taux.DoesNotExist:
        taux_usd = None
    return render(request, 'pharmacy/produit_detail.html', {
        'produit': produit,
        'taux_usd': taux_usd,
    })


# ============ CLIENT CRUD ============

@login_required
def client_list(request):
    from django.db.models import Count, Sum
    clients = Client.objects.annotate(
        nb_achats=Count('vente'),
        total_depense=Sum('vente__montant_total')
    ).all()
    
    stats_clients = {
        'total_clients': clients.count(),
        'clients_actifs': clients.filter(nb_achats__gt=0).count(),
        'total_ca_clients': sum(c.total_depense or 0 for c in clients),
    }
    return render(request, 'pharmacy/client_list.html', {
        'clients': clients,
        'stats': stats_clients,
    })


@login_required
def client_create(request):
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Client créé avec succès.")
            return redirect('client_list')
    else:
        form = ClientForm()
    return render(request, 'pharmacy/client_form.html', {'form': form, 'title': 'Nouveau Client'})


@non_vendeur_required
def client_edit(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, "Client modifié avec succès.")
            return redirect('client_list')
    else:
        form = ClientForm(instance=client)
    return render(request, 'pharmacy/client_form.html', {'form': form, 'title': 'Modifier Client'})


@non_vendeur_required
def client_delete(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        client.delete()
        messages.success(request, "Client supprimé avec succès.")
        return redirect('client_list')
    return render(request, 'pharmacy/confirm_delete.html', {'object': client, 'type': 'Client'})


# ============ VENTE CRUD ============

@login_required
def vente_home(request):
    """Page d'accueil des ventes avec choix d'action"""
    aujourd_hui = date.today()
    debut_mois = aujourd_hui.replace(day=1)
    
    ventes_jour = Vente.objects.filter(date_vente__date=aujourd_hui)
    stats = {
        'total_ventes': Vente.objects.count(),
        'ventes_jour': ventes_jour.count(),
        'ca_jour': ventes_jour.aggregate(total=models.Sum('montant_total'))['total'] or 0,
        'ca_mois': Vente.objects.filter(date_vente__date__gte=debut_mois).aggregate(
            total=models.Sum('montant_total'))['total'] or 0,
        'comptant_jour': ventes_jour.filter(mode_paiement='comptant').count(),
        'credit_jour': ventes_jour.filter(mode_paiement='credit').count(),
        'produits_alerte': Produit.objects.filter(
            quantite_stock__lte=models.F('quantite_alerte')).count(),
    }
    
    return render(request, 'pharmacy/vente_home.html', {'stats': stats})


@non_vendeur_required
def vente_edit(request, pk):
    """Modifier une vente existante"""
    vente = get_object_or_404(Vente, pk=pk)
    lignes = vente.lignes.select_related('produit').all()
    
    if request.method == 'POST':
        # Logique de modification de la vente
        form = VenteCompletForm(request.POST, instance=vente)
        lignes_data = json.loads(request.POST.get('lignes_json', '[]'))
        
        if form.is_valid() and lignes_data:
            # Supprimer les anciennes lignes
            vente.lignes.all().delete()
            
            # Remettre en stock les anciennes quantités (déjà fait lors de la suppression)
            
            # Recréer les lignes
            total_vente = 0
            for ligne_data in lignes_data:
                produit = Produit.objects.get(pk=ligne_data['produit_id'])
                quantite = ligne_data['quantite']
                prix_unitaire = ligne_data['prix_unitaire']
                montant_ligne = ligne_data['montant_ligne']
                
                LigneVente.objects.create(
                    vente=vente,
                    produit=produit,
                    quantite=quantite,
                    prix_unitaire=prix_unitaire,
                    montant_ligne=montant_ligne
                )
                
                produit.quantite_stock -= quantite
                produit.save()
                total_vente += montant_ligne
            
            vente.montant_total = total_vente
            if total_vente >= Decimal('10000'):
                vente.montant_remise = (total_vente * vente.remise_pourcent / Decimal('100')).quantize(Decimal('0.01'))
            else:
                vente.montant_remise = Decimal('0')
            vente.montant_net = total_vente - vente.montant_remise
            vente.save()
            
            messages.success(request, f"Vente #{vente.code_vente} modifiée avec succès.")
            return redirect('vente_detail', pk=vente.pk)
    else:
        form = VenteCompletForm(instance=vente)
        
        # Préparer les données des lignes pour le formulaire
        lignes_data = []
        for ligne in lignes:
            lignes_data.append({
                'produit_id': ligne.produit.pk,
                'nom': ligne.produit.designation,
                'quantite': ligne.quantite,
                'stock_max': ligne.produit.quantite_stock + ligne.quantite,  # Stock disponible si on annule cette ligne
                'prix_unitaire': float(ligne.prix_unitaire),
                'montant_ligne': float(ligne.montant_ligne)
            })
    
    # Produits disponibles pour l'autocomplétion
    produits_disponibles = Produit.objects.filter(quantite_stock__gt=0).select_related('fournisseur').order_by('designation')
    
    # Préparer les données JSON pour l'autocomplétion
    import json
    produits_data = []
    for p in produits_disponibles:
        produits_data.append({
            'id': p.pk,
            'nom': p.designation,
            'prix': float(p.prix_vente),
            'stock': p.quantite_stock,
            'recherche': p.designation.lower()
        })
    produits_json = json.dumps(produits_data)
    lignes_json = json.dumps(lignes_data)
    
    return render(request, 'pharmacy/vente_form.html', {
        'form': form,
        'title': f'Modifier Vente #{vente.code_vente}',
        'vente': vente,
        'produits_disponibles': produits_disponibles,
        'produits_json': produits_json,
        'lignes_json': lignes_json,
        'is_edit': True,
        'taux_remise': vente.remise_pourcent,
    })


@login_required
def vente_list(request):
    ventes = Vente.objects.select_related('client', 'vendeur').prefetch_related('lignes__produit').all()
    
    aujourd_hui = date.today()
    ventes_jour = ventes.filter(date_vente__date=aujourd_hui)
    stats_ventes = {
        'total_ventes': ventes.count(),
        'ventes_jour': ventes_jour.count(),
        'ca_jour': sum(v.montant_total for v in ventes_jour),
        'ca_total': sum(v.montant_total for v in ventes),
        'comptant_jour': ventes_jour.filter(mode_paiement='comptant').count(),
        'credit_jour': ventes_jour.filter(mode_paiement='credit').count(),
    }
    return render(request, 'pharmacy/vente_list.html', {
        'ventes': ventes,
        'stats': stats_ventes,
    })


@login_required
def vente_credit_list(request):
    """Liste des ventes à crédit non soldées"""
    ventes_credit = Vente.objects.filter(mode_paiement='credit', est_solde=False).select_related('client', 'vendeur').order_by('-date_vente')
    ventes_soldees = Vente.objects.filter(mode_paiement='credit', est_solde=True).select_related('client', 'vendeur').order_by('-date_vente')[:20]
    
    total_impaye = sum(v.montant_total - v.montant_paye for v in ventes_credit)
    
    return render(request, 'pharmacy/vente_credit_list.html', {
        'ventes_credit': ventes_credit,
        'ventes_soldees': ventes_soldees,
        'total_impaye': total_impaye,
    })


@non_vendeur_required
def vente_credit_payer(request, pk):
    """Enregistrer un paiement sur une vente à crédit"""
    vente = get_object_or_404(Vente, pk=pk, mode_paiement='credit')
    
    if request.method == 'POST':
        montant = request.POST.get('montant', 0)
        try:
            from decimal import Decimal
            montant = Decimal(str(montant))
            reste = vente.montant_total - vente.montant_paye
            
            if montant <= 0:
                messages.error(request, "Le montant doit être supérieur à 0.")
            elif montant > reste:
                messages.error(request, f"Le montant dépasse le reste à payer ({reste} FC).")
            else:
                vente.montant_paye += montant
                if vente.montant_paye >= vente.montant_total:
                    vente.est_solde = True
                vente.save()
                enregistrer_historique(request.user, 'paiement', 'Vente', f"Paiement {montant} FC sur vente #{vente.code_vente}")
                messages.success(request, f"Paiement de {montant} FC enregistré. Reste: {vente.montant_total - vente.montant_paye} FC")
        except (ValueError, Exception) as e:
            messages.error(request, f"Erreur: {e}")
    
    return redirect('vente_credit_list')


@login_required
def analyse_clients(request):
    """Analyse des clients : fréquence d'achat et total dépensé"""
    from django.db.models import Count, Sum, Q
    
    # Statistiques des clients
    clients_stats = []
    clients = Client.objects.annotate(
        nombre_ventes=Count('vente'),
        total_depense=Sum('vente__montant_total')
    ).filter(nombre_ventes__gt=0).order_by('-total_depense')
    
    for client in clients:
        # Produits achetés par ce client
        produits_achetes = {}
        ventes_client = Vente.objects.filter(client=client).prefetch_related('lignes__produit')
        
        for vente in ventes_client:
            for ligne in vente.lignes.all():
                produit = ligne.produit.designation
                if produit not in produits_achetes:
                    produits_achetes[produit] = {'quantite': 0, 'montant': 0}
                produits_achetes[produit]['quantite'] += ligne.quantite
                produits_achetes[produit]['montant'] += ligne.montant_ligne
        
        clients_stats.append({
            'client': client,
            'nombre_ventes': client.nombre_ventes,
            'total_depense': client.total_depense or 0,
            'panier_moyen': (client.total_depense or 0) / client.nombre_ventes if client.nombre_ventes > 0 else 0,
            'produits_achetes': produits_achetes,
            'premier_achat': ventes_client.order_by('date_vente').first().date_vente if ventes_client.exists() else None,
            'dernier_achat': ventes_client.order_by('-date_vente').first().date_vente if ventes_client.exists() else None,
        })
    
    # Meilleur client (total dépensé)
    meilleur_client = max(clients_stats, key=lambda x: x['total_depense']) if clients_stats else None
    
    # Client le plus fidèle (nombre d'achats)
    client_fidele = max(clients_stats, key=lambda x: x['nombre_ventes']) if clients_stats else None
    
    context = {
        'clients_stats': clients_stats,
        'meilleur_client': meilleur_client,
        'client_fidele': client_fidele,
        'total_clients': len(clients_stats),
        'total_ventes': sum(c['nombre_ventes'] for c in clients_stats),
        'total_ca': sum(c['total_depense'] for c in clients_stats),
    }
    
    return render(request, 'pharmacy/analyse_clients.html', context)


@login_required
def vente_create(request):
    produits_disponibles = Produit.objects.filter(quantite_stock__gt=0).select_related('fournisseur').order_by('designation')
    
    # Préparer les données JSON pour l'autocomplétion
    import json
    produits_data = []
    for p in produits_disponibles:
        produits_data.append({
            'id': p.pk,
            'nom': p.designation,
            'prix': float(p.prix_vente),
            'stock': p.quantite_stock,
            'recherche': p.designation.lower()
        })
    produits_json = json.dumps(produits_data)
    
    if request.method == 'POST':
        form = VenteCompletForm(request.POST)
        lignes_data = json.loads(request.POST.get('lignes_json', '[]'))

        if form.is_valid() and lignes_data:
            nouveau_nom = form.cleaned_data.get('nouveau_client_nom', '').strip()
            client = form.cleaned_data.get('client')
            if nouveau_nom and not client:
                client = Client.objects.create(
                    nom=nouveau_nom,
                    telephone=form.cleaned_data.get('nouveau_client_telephone', ''),
                    adresse=form.cleaned_data.get('nouveau_client_adresse', ''),
                )

            vente = form.save(commit=False)
            vente.client = client
            vente.vendeur = request.user
            vente.save()

            erreurs = []
            for ld in lignes_data:
                try:
                    produit = Produit.objects.get(pk=ld['produit_id'])
                    qte = int(ld['quantite'])
                    if qte > produit.quantite_stock:
                        erreurs.append(f"Stock insuffisant pour {produit.designation} (dispo: {produit.quantite_stock})")
                        continue
                    prix = produit.prix_vente
                    LigneVente.objects.create(
                        vente=vente, produit=produit, quantite=qte,
                        prix_unitaire=prix, montant_ligne=qte * prix
                    )
                    produit.quantite_stock -= qte
                    produit.save()
                except (Produit.DoesNotExist, ValueError, KeyError):
                    continue

            vente.calculer_total()
            
            # Gérer le mode de paiement
            if vente.mode_paiement == 'comptant':
                vente.montant_paye = vente.montant_net
                vente.est_solde = True
            else:
                vente.montant_paye = 0
                vente.est_solde = False
            vente.save()
            
            enregistrer_historique(request.user, 'creation', 'Vente', f"Vente #{vente.code_vente} - {vente.montant_total} FC")
            for err in erreurs:
                messages.warning(request, err)
            messages.success(request, f"Vente #{vente.code_vente} enregistrée avec succès.")
            from django.urls import reverse
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'detail_url': reverse('vente_detail', args=[vente.pk]),
                    'facture_url': reverse('facture_pdf', args=[vente.pk]),
                    'montant_total': float(vente.montant_total or 0),
                    'montant_remise': float(vente.montant_remise or 0),
                    'montant_net': float(vente.montant_net or 0),
                    'remise_pourcent': float(vente.remise_pourcent or 0),
                })
            return redirect('vente_detail', pk=vente.pk)
        else:
            if not lignes_data:
                messages.error(request, "Ajoutez au moins un produit à la vente.")
    else:
        form = VenteCompletForm()

    return render(request, 'pharmacy/vente_form.html', {
        'form': form,
        'title': 'Nouvelle Vente',
        'produits_disponibles': produits_disponibles,
        'produits_json': produits_json,
        'taux_remise': 2,
    })


@login_required
def api_produit_info(request, pk):
    try:
        p = Produit.objects.select_related('fournisseur').get(pk=pk)
        return JsonResponse({
            'designation': p.designation,
            'prix_vente': float(p.prix_vente),
            'quantite_stock': p.quantite_stock,
        })
    except Produit.DoesNotExist:
        return JsonResponse({'error': 'Produit non trouvé'}, status=404)


@login_required
def vente_detail(request, pk):
    vente = get_object_or_404(Vente, pk=pk)
    lignes = vente.lignes.select_related('produit').all()
    form = LigneVenteForm()
    return render(request, 'pharmacy/vente_detail.html', {
        'vente': vente, 'lignes': lignes, 'form': form
    })


@login_required
def vente_add_ligne(request, pk):
    vente = get_object_or_404(Vente, pk=pk)
    if request.method == 'POST':
        form = LigneVenteForm(request.POST)
        if form.is_valid():
            ligne = form.save(commit=False)
            ligne.vente = vente
            produit = ligne.produit
            if ligne.quantite > produit.quantite_stock:
                messages.error(request, f"Stock insuffisant pour {produit.designation}. Stock disponible: {produit.quantite_stock}")
                return redirect('vente_detail', pk=pk)
            ligne.prix_unitaire = produit.prix_vente
            ligne.montant_ligne = ligne.quantite * ligne.prix_unitaire
            ligne.save()
            produit.quantite_stock -= ligne.quantite
            produit.save()
            vente.calculer_total()
            messages.success(request, f"{produit.designation} ajouté à la vente.")
    return redirect('vente_detail', pk=pk)


@non_vendeur_required
def vente_remove_ligne(request, pk, ligne_pk):
    ligne = get_object_or_404(LigneVente, pk=ligne_pk, vente__pk=pk)
    if request.method == 'POST':
        produit = ligne.produit
        produit.quantite_stock += ligne.quantite
        produit.save()
        ligne.delete()
        vente = get_object_or_404(Vente, pk=pk)
        vente.calculer_total()
        messages.success(request, "Ligne supprimée.")
    return redirect('vente_detail', pk=pk)


@non_vendeur_required
def vente_delete(request, pk):
    vente = get_object_or_404(Vente, pk=pk)
    if request.method == 'POST':
        for ligne in vente.lignes.all():
            produit = ligne.produit
            produit.quantite_stock += ligne.quantite
            produit.save()
        vente.delete()
        messages.success(request, "Vente supprimée avec succès.")
        return redirect('vente_list')
    return render(request, 'pharmacy/confirm_delete.html', {'object': vente, 'type': 'Vente'})


# ============ LISTE PRODUITS PDF ============

@login_required
def produits_liste_pdf(request):
    """Générer un PDF avec la liste de tous les produits en stock"""
    from django.db.models import Sum
    
    produits = Produit.objects.select_related('fournisseur').all().order_by('designation')
    
    total_qte_initiale = produits.aggregate(total=Sum('quantite_initiale'))['total'] or 0
    total_qte_stock = produits.aggregate(total=Sum('quantite_stock'))['total'] or 0
    
    template = get_template('pharmacy/produits_liste_pdf.html')
    context = {
        'produits': produits,
        'total_produits': produits.count(),
        'total_qte_initiale': total_qte_initiale,
        'total_qte_stock': total_qte_stock,
        'date_impression': timezone.now(),
        'utilisateur': request.user.get_full_name() or request.user.username,
    }
    html = template.render(context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'filename="liste_produits.pdf"'
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse("Erreur lors de la génération du PDF", status=500)
    return response


# ============ FACTURE PDF ============

@login_required
def facture_pdf(request, pk):
    vente = get_object_or_404(Vente, pk=pk)
    lignes = list(vente.lignes.select_related('produit').all())
    heure_facture = vente.date_vente.strftime('%H:%M:%S')
    # Papier thermique 80mm : pas de limite fixe, toutes les lignes sur une seule page
    LIGNES_PAR_PAGE = 9999
    pages = []
    for i in range(0, len(lignes), LIGNES_PAR_PAGE):
        chunk = lignes[i:i + LIGNES_PAR_PAGE]
        pages.append({
            'lignes': chunk,
            'start_num': i + 1,
        })
    if not pages:
        pages = [{'lignes': [], 'start_num': 1}]
    template = get_template('pharmacy/facture_pdf.html')
    context = {
        'vente': vente,
        'pages': pages,
        'total_pages': len(pages),
        'date_du_jour': timezone.now(),
        'heure_facture': heure_facture,
    }
    html = template.render(context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'filename="facture_{vente.code_vente}.pdf"'
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse("Erreur lors de la génération du PDF", status=500)
    return response


# ============ RAPPORT JOURNALIER PDF ============

@login_required
def rapport_journalier_pdf(request):
    """Générer le rapport journalier PDF pour un vendeur"""
    import os, base64
    from datetime import date as dt_date
    
    # Date du rapport (aujourd'hui par défaut, ou paramètre GET)
    date_str = request.GET.get('date')
    if date_str:
        try:
            from datetime import datetime
            date_rapport = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            date_rapport = dt_date.today()
    else:
        date_rapport = dt_date.today()
    
    # Vendeur (soi-même par défaut, ou paramètre GET pour admin)
    vendeur_id = request.GET.get('vendeur')
    if vendeur_id and request.user.is_admin:
        from accounts.models import CustomUser
        vendeur = get_object_or_404(CustomUser, pk=vendeur_id)
    else:
        vendeur = request.user
    
    # Ventes du jour pour ce vendeur
    ventes_jour = Vente.objects.filter(
        vendeur=vendeur,
        date_vente__date=date_rapport
    ).select_related('client').prefetch_related('lignes__produit').order_by('date_vente')
    
    ventes_comptant = [v for v in ventes_jour if v.mode_paiement == 'comptant']
    ventes_credit = [v for v in ventes_jour if v.mode_paiement == 'credit']
    
    total_comptant = sum(v.montant_total for v in ventes_comptant)
    total_credit = sum(v.montant_total for v in ventes_credit)
    total_general = total_comptant + total_credit
    
    total_remise_comptant = sum(v.montant_remise for v in ventes_comptant)
    total_remise_credit = sum(v.montant_remise for v in ventes_credit)
    total_remise = total_remise_comptant + total_remise_credit
    
    total_net_comptant = sum(v.montant_net for v in ventes_comptant)
    total_net_credit = sum(v.montant_net for v in ventes_credit)
    total_net = total_net_comptant + total_net_credit
    
    # Historique du jour (suppressions, modifications, etc.)
    historiques = Historique.objects.filter(
        utilisateur=vendeur,
        date_action__date=date_rapport
    ).exclude(action='creation').exclude(action='connexion').order_by('date_action')
    
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo.png')
    logo_data = ''
    if os.path.exists(logo_path):
        with open(logo_path, 'rb') as f:
            logo_data = 'data:image/png;base64,' + base64.b64encode(f.read()).decode('utf-8')
    template = get_template('pharmacy/rapport_journalier_pdf.html')
    context = {
        'vendeur': vendeur,
        'date_rapport': date_rapport,
        'date_impression': timezone.now(),
        'ventes_comptant': ventes_comptant,
        'ventes_credit': ventes_credit,
        'total_comptant': total_comptant,
        'total_credit': total_credit,
        'total_general': total_general,
        'total_remise_comptant': total_remise_comptant,
        'total_remise_credit': total_remise_credit,
        'total_remise': total_remise,
        'total_net_comptant': total_net_comptant,
        'total_net_credit': total_net_credit,
        'total_net': total_net,
        'historiques': historiques,
        'logo_data': logo_data,
    }
    html = template.render(context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'filename="rapport_{vendeur.username}_{date_rapport}.pdf"'
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse("Erreur lors de la génération du PDF", status=500)
    return response


# ============ HISTORIQUE / AUDIT ============

def enregistrer_historique(user, action, modele='', detail=''):
    Historique.objects.create(
        utilisateur=user, action=action, modele=modele, detail=detail
    )


@login_required
def historique_ventes(request):
    """Historique complet de toutes les ventes avec total des montants"""
    from django.db.models import Sum, Count
    ventes = Vente.objects.select_related('client', 'vendeur').prefetch_related('lignes__produit').all()

    # Filtres optionnels
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    vendeur_id = request.GET.get('vendeur')
    mode = request.GET.get('mode')

    if date_debut:
        ventes = ventes.filter(date_vente__date__gte=date_debut)
    if date_fin:
        ventes = ventes.filter(date_vente__date__lte=date_fin)
    if vendeur_id:
        ventes = ventes.filter(vendeur_id=vendeur_id)
    if mode and mode in ('comptant', 'credit'):
        ventes = ventes.filter(mode_paiement=mode)

    total_montant = ventes.aggregate(total=Sum('montant_total'))['total'] or 0
    total_comptant = ventes.filter(mode_paiement='comptant').aggregate(total=Sum('montant_total'))['total'] or 0
    total_credit = ventes.filter(mode_paiement='credit').aggregate(total=Sum('montant_total'))['total'] or 0

    from accounts.models import User
    vendeurs = User.objects.filter(is_active=True)

    return render(request, 'pharmacy/historique_ventes.html', {
        'ventes': ventes,
        'total_montant': total_montant,
        'total_comptant': total_comptant,
        'total_credit': total_credit,
        'nb_ventes': ventes.count(),
        'vendeurs': vendeurs,
        'filtre_date_debut': date_debut or '',
        'filtre_date_fin': date_fin or '',
        'filtre_vendeur': vendeur_id or '',
        'filtre_mode': mode or '',
    })


@login_required
def historique_list(request):
    if not request.user.is_admin and not request.user.is_gestionnaire:
        messages.error(request, "Accès réservé à l'administrateur.")
        return redirect('dashboard')

    from accounts.models import User as UserModel
    qs = Historique.objects.select_related('utilisateur').all()

    filtre_user = request.GET.get('utilisateur', '').strip()
    filtre_module = request.GET.get('module', '').strip()

    if filtre_user:
        qs = qs.filter(utilisateur__pk=filtre_user)
    if filtre_module:
        qs = qs.filter(modele=filtre_module)

    historiques = qs[:500]
    utilisateurs = UserModel.objects.filter(is_active=True).order_by('first_name', 'last_name', 'username')
    modules = Historique.objects.values_list('modele', flat=True).distinct().exclude(modele='').order_by('modele')

    return render(request, 'pharmacy/historique_list.html', {
        'historiques': historiques,
        'utilisateurs': utilisateurs,
        'modules': modules,
        'filtre_user': filtre_user,
        'filtre_module': filtre_module,
    })


# ============ INVENTAIRE ============

@admin_gerant_required
def inventaire_list(request):
    """Liste de tous les inventaires."""
    inventaires = Inventaire.objects.select_related('utilisateur').all()
    return render(request, 'pharmacy/inventaire_list.html', {
        'inventaires': inventaires,
    })


@login_required
def inventaire_mes_comptages(request):
    """Liste des inventaires auxquels l'utilisateur est autorisé pour le comptage."""
    if is_admin_or_gerant(request.user):
        return redirect('inventaire_list')

    inventaires = Inventaire.objects.filter(
        compteurs_autorises=request.user
    ).select_related('utilisateur').order_by('-date_creation').distinct()

    return render(request, 'pharmacy/inventaire_mes_comptages.html', {
        'inventaires': inventaires,
    })


@admin_gerant_required
def inventaire_create(request):
    """Démarre un nouvel inventaire en brouillon avec snapshot du stock théorique."""
    from accounts.models import User as UserModel
    compteurs_disponibles = UserModel.objects.filter(
        is_active=True,
        role__in=['vendeur', 'gestionnaire', 'controleur'],
    ).order_by('first_name', 'last_name', 'username')

    if request.method == 'POST':
        observation = request.POST.get('observation', '').strip()
        inv = Inventaire.objects.create(
            utilisateur=request.user,
            statut='brouillon',
            observation=observation,
        )
        user_ids = request.POST.getlist('compteurs')
        if user_ids:
            eligibles = compteurs_disponibles.filter(pk__in=user_ids)
            inv.compteurs_autorises.set(eligibles)
        # Snapshot: une ligne par produit avec stock théorique = stock actuel
        produits = Produit.objects.all().order_by('designation')
        lignes = [
            LigneInventaire(
                inventaire=inv,
                produit=p,
                stock_theorique=p.quantite_stock,
                stock_physique=p.quantite_stock,
                prix_achat=p.prix_achat,
            )
            for p in produits
        ]
        LigneInventaire.objects.bulk_create(lignes)
        # bulk_create ne déclenche pas save() → on recalcule l'écart manuellement (déjà 0)
        inv.recalculer_totaux()
        inv.save()
        enregistrer_historique(request.user, 'creation', 'Inventaire',
                               f"Inventaire #{inv.code_inventaire} démarré ({inv.nb_produits_comptes} produits)")
        messages.success(request, f"Inventaire #{inv.code_inventaire} créé. Procédez à la saisie du comptage.")
        return redirect('inventaire_saisie', pk=inv.pk)
    return render(request, 'pharmacy/inventaire_form.html', {
        'compteurs_disponibles': compteurs_disponibles,
    })


@login_required
def inventaire_saisie(request, pk):
    """Saisie du stock physique. Accessible uniquement si statut = brouillon."""
    inv = get_object_or_404(Inventaire.objects.prefetch_related('compteurs_autorises'), pk=pk)
    if not can_count_inventory(request.user, inv):
        messages.error(request, "Vous n'êtes pas autorisé à effectuer le comptage de cet inventaire.")
        return redirect('dashboard')

    can_see_sensitive_data = is_admin_or_gerant(request.user)

    if inv.statut != 'brouillon':
        messages.warning(request, "Cet inventaire est déjà validé et ne peut plus être modifié.")
        return redirect('inventaire_detail', pk=inv.pk)

    lignes = inv.lignes.select_related('produit').order_by('produit__designation')
    return render(request, 'pharmacy/inventaire_saisie.html', {
        'inventaire': inv,
        'lignes': lignes,
        'can_see_sensitive_data': can_see_sensitive_data,
        'can_validate_inventory': can_see_sensitive_data,
        'can_recount': can_see_sensitive_data,
    })


@login_required
def inventaire_ligne_compter(request, pk, ligne_pk):
    """Endpoint AJAX : marque une ligne comme comptée et enregistre le stock physique saisi."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST requis'}, status=405)
    inv = get_object_or_404(Inventaire.objects.prefetch_related('compteurs_autorises'), pk=pk)
    if not can_count_inventory(request.user, inv):
        return JsonResponse({'success': False, 'error': 'Accès refusé'}, status=403)

    can_see_sensitive_data = is_admin_or_gerant(request.user)

    if inv.statut != 'brouillon':
        return JsonResponse({'success': False, 'error': 'Inventaire non modifiable'}, status=400)
    ligne = get_object_or_404(LigneInventaire, pk=ligne_pk, inventaire=inv)

    # En mode opérateur (non admin/gérant), une ligne déjà comptée est verrouillée.
    if ligne.comptee and not can_see_sensitive_data:
        return JsonResponse({'success': False, 'error': 'Cette ligne est déjà comptée et verrouillée.'}, status=400)

    val = request.POST.get('stock_physique', '').strip()
    if val == '':
        return JsonResponse({'success': False, 'error': 'Valeur requise'}, status=400)
    try:
        qte = int(val)
        if qte < 0:
            raise ValueError
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Valeur invalide'}, status=400)

    ligne.stock_physique = qte
    ligne.comptee = True
    ligne.save()
    inv.recalculer_totaux()
    inv.save()

    payload = {
        'success': True,
        'ligne_id': ligne.pk,
        'stock_physique': ligne.stock_physique,
        'comptee': ligne.comptee,
        'nb_comptees': inv.nb_comptees,
        'nb_non_comptees': inv.nb_non_comptees,
    }
    if can_see_sensitive_data:
        payload.update({
            'ecart': ligne.ecart,
            'valeur_ecart': float(ligne.valeur_ecart),
            'nb_ecarts': inv.nb_ecarts,
            'total_ecart_valeur': float(inv.total_ecart_valeur),
        })
    return JsonResponse(payload)


@admin_gerant_required
def inventaire_valider(request, pk):
    """Récap + validation finale. Applique les stocks physiques sur les produits."""
    inv = get_object_or_404(Inventaire, pk=pk)
    if inv.statut != 'brouillon':
        messages.warning(request, "Cet inventaire est déjà validé.")
        return redirect('inventaire_detail', pk=inv.pk)

    lignes = inv.lignes.select_related('produit').order_by('produit__designation')

    # Blocage si des produits n'ont pas été comptés
    non_comptees = [l for l in lignes if not l.comptee]
    if non_comptees:
        messages.error(
            request,
            f"Impossible de valider : {len(non_comptees)} produit(s) n'ont pas encore été comptés. "
            "Cliquez sur ✓ pour chaque ligne après comptage."
        )
        return redirect('inventaire_saisie', pk=inv.pk)

    if request.method == 'POST':
        from django.db import transaction
        with transaction.atomic():
            for ligne in lignes:
                if ligne.ecart != 0:
                    produit = ligne.produit
                    produit.quantite_stock = ligne.stock_physique
                    produit.save()
            inv.statut = 'valide'
            inv.date_validation = timezone.now()
            inv.recalculer_totaux()
            inv.save()
        enregistrer_historique(
            request.user, 'modification', 'Inventaire',
            f"Inventaire #{inv.code_inventaire} validé — {inv.nb_ecarts} écart(s), valeur: {inv.total_ecart_valeur} FC"
        )
        messages.success(request, f"Inventaire #{inv.code_inventaire} validé. Stocks mis à jour.")
        return redirect('inventaire_detail', pk=inv.pk)

    return render(request, 'pharmacy/inventaire_valider.html', {
        'inventaire': inv,
        'lignes': lignes,
        'lignes_ecart': [l for l in lignes if l.ecart != 0],
    })


@admin_gerant_required
def inventaire_detail(request, pk):
    """Consultation d'un inventaire (validé ou non)."""
    inv = get_object_or_404(Inventaire.objects.prefetch_related('compteurs_autorises'), pk=pk)

    if request.method == 'POST' and inv.statut == 'brouillon':
        user_ids = request.POST.getlist('compteurs')
        from accounts.models import User
        eligibles = User.objects.filter(
            is_active=True,
            role__in=['vendeur', 'gestionnaire', 'controleur'],
            pk__in=user_ids,
        )
        inv.compteurs_autorises.set(eligibles)
        enregistrer_historique(
            request.user,
            'modification',
            'Inventaire',
            f"Inventaire #{inv.code_inventaire} - mise à jour des compteurs autorisés ({eligibles.count()} utilisateur(s))"
        )
        messages.success(request, "Liste des compteurs autorisés mise à jour.")
        return redirect('inventaire_detail', pk=inv.pk)

    lignes = inv.lignes.select_related('produit').order_by('produit__designation')
    from accounts.models import User
    compteurs_disponibles = User.objects.filter(
        is_active=True,
        role__in=['vendeur', 'gestionnaire', 'controleur']
    ).order_by('first_name', 'last_name', 'username')

    return render(request, 'pharmacy/inventaire_detail.html', {
        'inventaire': inv,
        'lignes': lignes,
        'compteurs_disponibles': compteurs_disponibles,
        'compteurs_selectionnes_ids': set(inv.compteurs_autorises.values_list('id', flat=True)),
    })


@admin_gerant_required
def inventaire_annuler(request, pk):
    """Annule un inventaire en brouillon (ne touche pas aux stocks)."""
    inv = get_object_or_404(Inventaire, pk=pk)
    if inv.statut != 'brouillon':
        messages.error(request, "Seul un inventaire en brouillon peut être annulé.")
        return redirect('inventaire_detail', pk=inv.pk)
    if request.method == 'POST':
        inv.statut = 'annule'
        inv.save()
        enregistrer_historique(request.user, 'suppression', 'Inventaire',
                               f"Inventaire #{inv.code_inventaire} annulé")
        messages.success(request, f"Inventaire #{inv.code_inventaire} annulé.")
        return redirect('inventaire_list')
    return render(request, 'pharmacy/confirm_delete.html', {'object': inv, 'type': 'Inventaire (annulation)'})


@admin_gerant_required
def inventaire_delete(request, pk):
    """Supprime définitivement un inventaire (et ses lignes)."""
    inv = get_object_or_404(Inventaire, pk=pk)
    if request.method == 'POST':
        code = inv.code_inventaire
        statut = inv.get_statut_display()
        inv.delete()
        enregistrer_historique(
            request.user,
            'suppression',
            'Inventaire',
            f"Inventaire #{code} supprimé définitivement (statut: {statut})"
        )
        messages.success(request, f"Inventaire #{code} supprimé définitivement.")
        return redirect('inventaire_list')
    return render(request, 'pharmacy/confirm_delete.html', {
        'object': inv,
        'type': 'Inventaire (suppression définitive)'
    })


@admin_gerant_required
def inventaire_pdf(request, pk):
    """PDF d'un inventaire avec tous les écarts."""
    import os, base64
    inv = get_object_or_404(Inventaire, pk=pk)
    lignes = inv.lignes.select_related('produit').order_by('produit__designation')

    logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo.png')
    logo_data = ''
    if os.path.exists(logo_path):
        with open(logo_path, 'rb') as f:
            logo_data = 'data:image/png;base64,' + base64.b64encode(f.read()).decode('utf-8')

    template = get_template('pharmacy/inventaire_pdf.html')
    context = {
        'inventaire': inv,
        'lignes': lignes,
        'date_impression': timezone.now(),
        'logo_data': logo_data,
    }
    html = template.render(context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'filename="inventaire_{inv.code_inventaire}.pdf"'
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse("Erreur lors de la génération du PDF", status=500)
    return response


# ============ RÉQUISITION ============

@login_required
def requisition_list(request):
    """Liste des produits ayant atteint ou dépassé le seuil d'alerte de stock."""
    from django.db.models import ExpressionWrapper, IntegerField, F
    produits = (
        Produit.objects.select_related('fournisseur')
        .filter(quantite_stock__lte=F('quantite_alerte'))
        .annotate(manquant=ExpressionWrapper(F('quantite_alerte') - F('quantite_stock'), output_field=IntegerField()))
        .order_by('fournisseur__designation', 'designation')
    )
    return render(request, 'pharmacy/requisition_list.html', {
        'produits': produits,
        'nb_produits': produits.count(),
    })


@login_required
def requisition_pdf(request):
    """PDF de la liste des produits en alerte de stock."""
    import os, base64
    from django.db.models import ExpressionWrapper, IntegerField, F
    produits = (
        Produit.objects.select_related('fournisseur')
        .filter(quantite_stock__lte=F('quantite_alerte'))
        .annotate(manquant=ExpressionWrapper(F('quantite_alerte') - F('quantite_stock'), output_field=IntegerField()))
        .order_by('fournisseur__designation', 'designation')
    )
    logo_data = None
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo.png')
    if os.path.exists(logo_path):
        with open(logo_path, 'rb') as f:
            logo_data = 'data:image/png;base64,' + base64.b64encode(f.read()).decode('utf-8')

    template = get_template('pharmacy/requisition_pdf.html')
    html = template.render({
        'produits': produits,
        'date_impression': timezone.now(),
        'logo_data': logo_data,
        'utilisateur': request.user,
    })
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'filename="requisition_{timezone.now().strftime("%Y%m%d_%H%M")}.pdf"'
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse("Erreur lors de la génération du PDF", status=500)
    return response
