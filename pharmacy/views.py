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
from .models import Categorie, Fournisseur, Produit, Client, Vente, LigneVente, Historique
from django.conf import settings
from .forms import (CategorieForm, FournisseurForm, ProduitForm,
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
        'total_categories': Categorie.objects.count(),
        'total_fournisseurs': Fournisseur.objects.count(),
        'total_clients': Client.objects.count(),
        'total_ventes': Vente.objects.count(),
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


# ============ CATEGORIE CRUD ============

@login_required
def categorie_list(request):
    categories = Categorie.objects.all()
    return render(request, 'pharmacy/categorie_list.html', {'categories': categories})


@non_vendeur_required
def categorie_create(request):
    if request.method == 'POST':
        form = CategorieForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Catégorie créée avec succès.")
            return redirect('categorie_list')
    else:
        form = CategorieForm()
    return render(request, 'pharmacy/categorie_form.html', {'form': form, 'title': 'Nouvelle Catégorie'})


@non_vendeur_required
def categorie_edit(request, pk):
    categorie = get_object_or_404(Categorie, pk=pk)
    if request.method == 'POST':
        form = CategorieForm(request.POST, instance=categorie)
        if form.is_valid():
            form.save()
            messages.success(request, "Catégorie modifiée avec succès.")
            return redirect('categorie_list')
    else:
        form = CategorieForm(instance=categorie)
    return render(request, 'pharmacy/categorie_form.html', {'form': form, 'title': 'Modifier Catégorie'})


@non_vendeur_required
def categorie_delete(request, pk):
    categorie = get_object_or_404(Categorie, pk=pk)
    if request.method == 'POST':
        try:
            categorie.delete()
            messages.success(request, "Catégorie supprimée avec succès.")
        except Exception:
            messages.error(request, "Impossible de supprimer cette catégorie (utilisée par des produits).")
        return redirect('categorie_list')
    return render(request, 'pharmacy/confirm_delete.html', {'object': categorie, 'type': 'Catégorie'})


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

@login_required
def produit_list(request):
    produits = Produit.objects.select_related('fournisseur', 'categorie').all()
    return render(request, 'pharmacy/produit_list.html', {'produits': produits})


@non_vendeur_required
def produit_create(request):
    if request.method == 'POST':
        form = ProduitForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Produit créé avec succès.")
            return redirect('produit_list')
    else:
        form = ProduitForm()
    return render(request, 'pharmacy/produit_form.html', {'form': form, 'title': 'Nouveau Produit'})


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


# ============ CLIENT CRUD ============

@login_required
def client_list(request):
    clients = Client.objects.all()
    return render(request, 'pharmacy/client_list.html', {'clients': clients})


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
def vente_list(request):
    ventes = Vente.objects.select_related('client', 'vendeur').all()
    return render(request, 'pharmacy/vente_list.html', {'ventes': ventes})


@login_required
def vente_create(request):
    produits_disponibles = Produit.objects.filter(quantite_stock__gt=0).select_related('fournisseur')
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
            enregistrer_historique(request.user, 'creation', 'Vente', f"Vente #{vente.code_vente} - {vente.montant_net} FC")
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
    import os
    vente = get_object_or_404(Vente, pk=pk)
    lignes = vente.lignes.select_related('produit').all()
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo.svg')
    template = get_template('pharmacy/facture_pdf.html')
    context = {
        'vente': vente,
        'lignes': lignes,
        'date_impression': timezone.now(),
        'logo_path': logo_path.replace('\\', '/'),
    }
    html = template.render(context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'filename="facture_{vente.code_vente}.pdf"'
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
