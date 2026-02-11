from django import forms
from django.forms import inlineformset_factory
from .models import Taux, Fournisseur, Produit, Client, Vente, LigneVente


class TauxForm(forms.ModelForm):
    class Meta:
        model = Taux
        fields = ['code_devise', 'montant_fc']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            'code_devise': 'Code Devise (ex: USD, EUR)',
            'montant_fc': 'Montant en FC',
        }
        for field, ph in placeholders.items():
            self.fields[field].widget.attrs['placeholder'] = ph
            self.fields[field].widget.attrs['class'] = 'form-control'
            self.fields[field].label = ''
            self.fields[field].initial = None


class FournisseurForm(forms.ModelForm):
    class Meta:
        model = Fournisseur
        fields = ['designation', 'marge_beneficiaire']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            'designation': 'Désignation Fournisseur',
            'marge_beneficiaire': 'Marge Bénéficiaire (%)',
        }
        for field, ph in placeholders.items():
            self.fields[field].widget.attrs['placeholder'] = ph
            self.fields[field].label = ''
            self.fields[field].initial = None


class ProduitForm(forms.ModelForm):
    date_expiration = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label='',
        required=False
    )

    class Meta:
        model = Produit
        fields = ['designation', 'prix_achat', 'quantite_stock', 'quantite_alerte',
                  'jours_alerte_expiration', 'fournisseur', 'date_expiration']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            'designation': 'Désignation Produit',
            'prix_achat': "Prix d'Achat (FC)",
            'quantite_stock': 'Quantité en Stock',
            'quantite_alerte': 'Quantité Alerte',
            'jours_alerte_expiration': 'Alerte Expiration (jours avant)',
        }
        for field, ph in placeholders.items():
            if field != 'date_expiration':
                self.fields[field].widget = forms.NumberInput(attrs={'placeholder': ph, 'class': 'form-control'}) if isinstance(self.fields[field].widget, forms.NumberInput) else self.fields[field].widget
                self.fields[field].widget.attrs['placeholder'] = ph
                self.fields[field].widget.attrs['class'] = 'form-control'
            self.fields[field].label = ''
            if field != 'date_expiration':
                self.fields[field].initial = None
        for field in ['fournisseur', 'date_expiration']:
            if field in self.fields:
                self.fields[field].label = ''
        if 'fournisseur' in self.fields:
            self.fields['fournisseur'].empty_label = '-- Fournisseur --'

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.pk:
            instance.quantite_initiale = instance.quantite_stock
        if commit:
            instance.save()
        return instance


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['nom', 'telephone', 'adresse']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            'nom': 'Nom du Client',
            'telephone': 'Téléphone',
            'adresse': 'Adresse',
        }
        for field, ph in placeholders.items():
            self.fields[field].widget.attrs['placeholder'] = ph
            self.fields[field].label = ''


class VenteForm(forms.ModelForm):
    class Meta:
        model = Vente
        fields = ['client', 'type_vente', 'observation']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['client'].label = ''
        self.fields['client'].empty_label = '-- Client (optionnel) --'
        self.fields['type_vente'].label = ''
        self.fields['type_vente'].choices = [('', '-- Type de Vente --')] + [
            c for c in self.fields['type_vente'].choices if c[0] != ''
        ]
        self.fields['observation'].label = ''
        self.fields['observation'].widget.attrs['placeholder'] = 'Observation (optionnel)'


class VenteCompletForm(forms.ModelForm):
    nouveau_client_nom = forms.CharField(
        required=False, label='',
        widget=forms.TextInput(attrs={'placeholder': 'Nom du nouveau client'})
    )
    nouveau_client_telephone = forms.CharField(
        required=False, label='',
        widget=forms.TextInput(attrs={'placeholder': 'T\u00e9l\u00e9phone (optionnel)'})
    )
    nouveau_client_adresse = forms.CharField(
        required=False, label='',
        widget=forms.TextInput(attrs={'placeholder': 'Adresse (optionnel)'})
    )

    class Meta:
        model = Vente
        fields = ['client', 'type_vente', 'mode_paiement', 'observation']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['client'].label = ''
        self.fields['client'].required = False
        self.fields['client'].empty_label = '-- Client existant --'
        self.fields['client'].widget.attrs.update({'class': 'form-select'})
        self.fields['type_vente'].label = ''
        self.fields['type_vente'].choices = [('', '-- Type de Vente --')] + [
            c for c in self.fields['type_vente'].choices if c[0] != ''
        ]
        self.fields['type_vente'].widget.attrs.update({'class': 'form-select'})
        self.fields['mode_paiement'].label = ''
        self.fields['mode_paiement'].widget.attrs.update({'class': 'form-select'})
        self.fields['observation'].label = ''
        self.fields['observation'].widget.attrs['placeholder'] = 'Observation (optionnel)'
        for f in ['nouveau_client_nom', 'nouveau_client_telephone', 'nouveau_client_adresse']:
            self.fields[f].widget.attrs.update({'class': 'form-control'})


class LigneVenteForm(forms.ModelForm):
    class Meta:
        model = LigneVente
        fields = ['produit', 'quantite']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['produit'].queryset = Produit.objects.filter(quantite_stock__gt=0)
        self.fields['produit'].label = ''
        self.fields['produit'].empty_label = '-- Choisir un produit --'
        self.fields['quantite'].label = ''
        self.fields['quantite'].widget.attrs['placeholder'] = 'Quantité'
        self.fields['quantite'].initial = None
