import random
import pandas as pd
import os
from datetime import datetime, timedelta

class Composant:
    """
    Représente la pièce physique qui s'use.
    Gère les scénarios de dégradation, de panne et de réparation imparfaite.
    """
    def __init__(self, id_asset, parametres):
        self.id = id_asset
        self.params = parametres
        self.usure = 0.0
        self.etat = "OPERATIONNEL" # OPERATIONNEL, EN_PANNE
        self.age = 0
        self.date_installation = datetime.now()

    def progresser(self, usage):
        """ SCÉNARIO 1 : Usure normale basée sur l'usage """
        if self.etat == "EN_PANNE":
            return

        self.age += 1
        # Calcul de l'incrément d'usure (vitesse * usage + variabilité)
        increment = (self.params['vitesse_usure'] * usage) + random.uniform(0, 0.02)
        self.usure += increment

        # SCÉNARIO 4 : Panne si l'usure dépasse le seuil critique
        if self.usure >= self.params['seuil_panne']:
            self.etat = "EN_PANNE"

    def restaurer(self, type_action):
        """ 
        Gère la remise en état.
        SCÉNARIO 7 : Réparation imparfaite vs Remplacement neuf.
        """
        if type_action == "REMPLACEMENT":
            self.usure = 0.0
            self.etat = "OPERATIONNEL"
            self.date_installation = datetime.now() # On repart à zéro
        elif type_action == "REPARATION":
            # On réduit l'usure mais il reste un dommage résiduel
            efficacite = self.params['efficacite_reparation']
            self.usure = self.usure * (1 - efficacite)
            self.etat = "OPERATIONNEL"

class Simulateur:
    """
    Gère la flotte de systèmes et applique la politique de maintenance.
    """
    def __init__(self, taille_flotte, parametres):
        self.flotte = [Composant(f"COMP-{i:03d}", parametres) for i in range(taille_flotte)]
        self.params = parametres
        self.evenements = []
        self.cout_total = 0

    def simuler_periode(self, jours):
        """ Boucle principale de simulation sur une durée donnée """
        for jour in range(1, jours + 1):
            for comp in self.flotte:
                # 1. Le composant s'use durant la journée
                usage_quotidien = random.uniform(0.7, 1.3)
                comp.progresser(usage_quotidien)

                # 2. Vérification des scénarios
                
                # CAS A : Panne détectée (Maintenance Corrective)
                if comp.etat == "EN_PANNE":
                    self.noter_action(jour, comp, "PANNE_CRITIQUE", self.params['cout_panne'])
                    comp.restaurer("REMPLACEMENT")
                    continue

                # CAS B : Maintenance Systématique (Calendaire - Scénario 8)
                if jour % self.params['frequence_systematique'] == 0:
                    self.noter_action(jour, comp, "MAINT_SYSTEMATIQUE", self.params['cout_remplacement'])
                    comp.restaurer("REMPLACEMENT")
                    continue

                # CAS C : Inspection et Maintenance Conditionnelle (Scénarios 2, 3, 5, 6)
                if jour % self.params['frequence_inspection'] == 0:
                    self.effectuer_inspection(jour, comp)

    def effectuer_inspection(self, jour, comp):
        """ Simule le diagnostic d'un logiciel de détection imparfait """
        reellement_use = comp.usure >= self.params['seuil_alerte']
        
        # Simulation des erreurs de détection
        alerte_declenchee = False
        if reellement_use:
            # Scénario 3 (Vrai Positif) ou Scénario 5 (Faux Négatif)
            alerte_declenchee = random.random() < self.params['sensibilite']
        else:
            # Scénario 2 (Vrai Négatif) ou Scénario 6 (Faux Positif)
            alerte_declenchee = random.random() < (1 - self.params['specificite'])

        if alerte_declenchee:
            # On intervient de manière préventive
            self.noter_action(jour, comp, "MAINT_PREVENTIVE", self.params['cout_reparation'])
            comp.restaurer("REPARATION")
        else:
            self.noter_action(jour, comp, "INSPECTION_RAS", 0)

    def noter_action(self, jour, comp, type_acte, cout):
        self.cout_total += cout
        self.evenements.append({
            "Jour": jour,
            "ID_Composant": comp.id,
            "Type_Evenement": type_acte,
            "Niveau_Usure": round(comp.usure, 2),
            "Cout_Associe": cout
        })

    def exporter_donnees(self, nom_fichier="data/resultats_simulation.csv"):
        """ Sauvegarde les résultats pour l'analyse ultérieure """
        os.makedirs("data", exist_ok=True)
        df = pd.DataFrame(self.evenements)
        df.to_csv(nom_fichier, index=False)
        print(f"✅ Données exportées avec succès dans : {nom_fichier}")

# --- ZONE DE TEST POUR LE CEO ---
if __name__ == "__main__":
    # Paramètres par défaut pour la démonstration
    reglages = {
        'vitesse_usure': 0.15,
        'seuil_panne': 20.0,
        'seuil_alerte': 12.0,
        'sensibilite': 0.90,      # 90% de chance de voir une usure réelle
        'specificite': 0.95,      # 5% de fausses alertes (Faux Positifs)
        'efficacite_reparation': 0.8,
        'frequence_inspection': 15,
        'frequence_systematique': 100,
        'cout_panne': 5000,
        'cout_remplacement': 1200,
        'cout_reparation': 400
    }

    # Lancement d'une simulation de 100 machines sur 1 an
    print("🚀 Lancement de la simulation ASIJA...")
    sim = Simulateur(taille_flotte=100, parametres=reglages)
    sim.simuler_periode(365)
    
    print(f"💰 Bilan financier : {sim.cout_total:,} €")
    sim.exporter_donnees()