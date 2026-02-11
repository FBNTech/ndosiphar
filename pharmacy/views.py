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
import json
from .models import Taux, Fournisseur, Produit, Client, Vente, LigneVente, Historique
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

    context = {
        'total_produits': Produit.objects.count(),
        'total_fournisseurs': Fournisseur.objects.count(),
        'total_clients': Client.objects.count(),
        'total_ventes': Vente.objects.count(),
        'total_taux': Taux.objects.count(),
        'dernier_taux': Taux.objects.first(),
        'ventes_jour': ventes_jour['total'] or 0,
        'ventes_jour_nombre': ventes_jour['nombre'],
        'ventes_semaine': ventes_semaine['total'] or 0,
        'ventes_semaine_nombre': ventes_semaine['nombre'],
        'ventes_mois': ventes_mois['total'] or 0,
        'ventes_mois_nombre': ventes_mois['nombre'],
        'produits_alerte': Produit.objects.filter(quantite_stock__lte=models.F('quantite_alerte')),
        'produits_expiration': Produit.objects.filter(
            date_expiration__lte=date.today() + timedelta(days=30)
        ).order_by('date_expiration'),
        'ventes_recentes': Vente.objects.all()[:5],
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


@non_vendeur_required
def taux_edit(request, pk):
    taux = get_object_or_404(Taux, pk=pk)
    if request.method == 'POST':
        form = TauxForm(request.POST, instance=taux)
        if form.is_valid():
            form.save()
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
            form.save()
            messages.success(request, "Fournisseur modifié avec succès.")
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
        form.fields['quantite_alerte'].initial = 10
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
def produit_edit(request, pk):
    produit = get_object_or_404(Produit, pk=pk)
    if request.method == 'POST':
        form = ProduitForm(request.POST, instance=produit)
        if form.is_valid():
            form.save()
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
                vente.montant_paye = vente.montant_total
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


# ============ FACTURE PDF ============

@login_required
def facture_pdf(request, pk):
    import os, base64
    vente = get_object_or_404(Vente, pk=pk)
    lignes = vente.lignes.select_related('produit').all()
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo.png')
    logo_data = ''
    if os.path.exists(logo_path):
        with open(logo_path, 'rb') as f:
            logo_data = 'data:image/png;base64,' + base64.b64encode(f.read()).decode('utf-8')
    template = get_template('pharmacy/facture_pdf.html')
    context = {
        'vente': vente,
        'lignes': lignes,
        'date_impression': timezone.now(),
        'logo_data': logo_data,
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
def historique_list(request):
    if not request.user.is_admin:
        messages.error(request, "Accès réservé à l'administrateur.")
        return redirect('dashboard')
    historiques = Historique.objects.select_related('utilisateur').all()[:200]
    return render(request, 'pharmacy/historique_list.html', {'historiques': historiques})
