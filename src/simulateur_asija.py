import random
import pandas as pd
import numpy as np

class Composant:
    """
    Représente un composant individuel (Asset).
    Gère son propre état d'usure et son cycle de vie.
    """
    def __init__(self, id_asset, params):
        self.id = id_asset
        self.params = params
        self.usure = 0.0
        self.etat = "OK"  # OK, EN_PANNE, RETIRE
        self.age = 0
        self.derniere_maintenance = 0

    def vieillir(self, usage):
        """ SCÉNARIO 1 : Vieillissement normal """
        if self.etat != "OK":
            return
        
        self.age += 1
        # Loi d'usure (Incrément = usage * alpha + bruit)
        taux = self.params.get('alpha', 0.1)
        bruit = random.uniform(0, 0.05)
        self.usure += (taux * usage) + bruit

        # SCÉNARIO 4 : Panne si l'usure dépasse le seuil critique
        if self.usure >= self.params.get('seuil_panne', 20.0):
            self.etat = "EN_PANNE"

class Simulateur:
    """
    Gestionnaire de la flotte et des politiques de maintenance.
    """
    def __init__(self, nb_systemes, params):
        self.nb_systemes = nb_systemes
        self.params = params
        # Initialisation de la flotte (Lot 3)
        self.flotte = [Composant(f"ASSET_{i:03d}", params) for i in range(nb_systemes)]
        self.historique = []
        self.cout_total = 0

    def executer_simulation(self, duree_jours):
        """ Boucle principale de simulation """
        for jour in range(1, duree_jours + 1):
            for comp in self.flotte:
                # 1. Vieillissement quotidien
                usage_jour = random.uniform(0.8, 1.2)
                comp.vieillir(usage_jour)

                # 2. SCÉNARIO 4 : Gestion de la panne (Correctif)
                if comp.etat == "EN_PANNE":
                    self.enregistrer_evenement(jour, comp, "PANNE", self.params['cout_panne'])
                    self.reparer(comp, "CORRECTIF")
                    continue

                # 3. SCÉNARIO 8 : Maintenance Systématique (Calendaire)
                intervalle_syst = self.params.get('intervalle_systematique')
                if intervalle_syst and (jour - comp.derniere_maintenance) >= intervalle_syst:
                    self.enregistrer_evenement(jour, comp, "MAINT_SYST", self.params['cout_remplacement'])
                    self.reparer(comp, "SYSTEMATIQUE")
                    continue

                # 4. SCÉNARIOS 2, 3, 5, 6 : Inspections (Conditionnel)
                if jour % self.params.get('frequence_inspection', 10) == 0:
                    self.effectuer_inspection(jour, comp)

    def effectuer_inspection(self, jour, comp):
        """ Simulation du détecteur imparfait """
        seuil_alerte = self.params['seuil_alerte']
        anomalie_reelle = comp.usure >= seuil_alerte
        
        # Logique du détecteur (Sensibilité / Spécificité)
        detecteur_sonne = False
        if anomalie_reelle:
            # SCÉNARIO 3 (Vrai +) ou SCÉNARIO 5 (Faux -)
            detecteur_sonne = random.random() < self.params['fiabilite_detecteur']
        else:
            # SCÉNARIO 6 (Faux +) ou SCÉNARIO 2 (Vrai -)
            detecteur_sonne = random.random() < (1 - self.params['specificite_detecteur'])

        if detecteur_sonne:
            # On déclenche une maintenance préventive
            self.enregistrer_evenement(jour, comp, "INSPECTION_ALERTE", self.params['cout_inspection'])
            self.reparer(comp, "PREVENTIF")
        else:
            self.enregistrer_evenement(jour, comp, "INSPECTION_RAS", self.params['cout_inspection'])

    def reparer(self, comp, declencheur):
        """ 
        Gère la réparation ou le remplacement.
        SCÉNARIO 7 : Réparation imparfaite.
        """
        if declencheur == "CORRECTIF" or comp.usure > self.params['seuil_panne'] * 0.9:
            # Remplacement à neuf (Coût élevé)
            comp.usure = 0.0
            comp.derniere_maintenance = comp.age
            comp.etat = "OK"
            self.cout_total += self.params['cout_remplacement']
        else:
            # SCÉNARIO 7 : Réparation (Coût faible, usure résiduelle)
            qualite = self.params['qualite_reparation']
            comp.usure = comp.usure * (1 - qualite)
            comp.etat = "OK"
            self.cout_total += self.params['cout_reparation']

    def enregistrer_evenement(self, jour, comp, type_ev, cout):
        self.cout_total += cout
        self.historique.append({
            "jour": jour,
            "asset_id": comp.id,
            "type": type_ev,
            "usure": round(comp.usure, 2),
            "cout": cout
        })

# --- PROGRAMME DE TEST ---
if __name__ == "__main__":
    parametres = {
        'alpha': 0.15,               # Vitesse usure
        'seuil_panne': 20.0,         # Panne à 20
        'seuil_alerte': 14.0,        # Alarme à 14
        'fiabilite_detecteur': 0.9,  # 90% de détection (Sensibilité)
        'specificite_detecteur': 0.95, # 5% de fausses alarmes
        'qualite_reparation': 0.7,   # 70% de l'usure enlevée
        'frequence_inspection': 15,  # Tous les 15 jours
        'intervalle_systematique': 100, # Remplacer tous les 100 jours quoi qu'il arrive
        'cout_inspection': 50,
        'cout_reparation': 400,
        'cout_remplacement': 1500,
        'cout_panne': 5000
    }

    sim = Simulateur(nb_systemes=100, params=parametres)
    sim.executer_simulation(365) # Simuler 1 an
    
    print(f"✅ Simulation terminée pour 100 systèmes.")
    print(f"💰 Coût total sur 1 an : {sim.cout_total:,} €")
    
    # Aperçu des données pour Jalil
    df = pd.DataFrame(sim.historique)
    print("\nRépartition des événements :")
    print(df['type'].value_counts())