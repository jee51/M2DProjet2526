import random
import numpy as np

class Systeme:
    def __init__(self, id_sys, params):
        """
        Initialise un système (une machine).
        params: dictionnaire contenant les seuils et probabilités.
        """
        self.id = id_sys
        self.params = params
        
        # État interne
        self.temps = 0
        self.usure = 0.0
        self.en_panne = False
        self.historique = [] # Pour stocker les événements
        self.derniere_maintenance = 0

    def vieillir(self, usage, dt=1):
        """
        SCÉNARIO 1 : Normal (rien ne se passe, juste de l'usure)
        Fait avancer le temps et l'usure.
        """
        if self.en_panne:
            return # Un système en panne ne s'use plus, il attend la réparation

        self.temps += dt
        
        # Loi de dégradation (Linéaire + Aléatoire pour commencer, ou Gamma)
        # usure_ajoutee = alpha * usage + bruit
        taux_usure = self.params.get('alpha', 0.1)
        usure_delta = (taux_usure * usage) + random.uniform(0, 0.05)
        self.usure += usure_delta

        # SCÉNARIO 4 : Panne entre deux inspections
        seuil_panne = self.params.get('seuil_panne', 20.0)
        if self.usure >= seuil_panne:
            self.en_panne = True
            self.enregistrer_event("PANNE", "Panne fonctionnelle (Usure trop haute)")

        # SCÉNARIO 8 : Remplacement préventif programmé (Systématique)
        intervalle_syst = self.params.get('intervalle_systematique', None)
        if intervalle_syst and (self.temps - self.derniere_maintenance) >= intervalle_syst:
            self.maintenir("REMPLACEMENT", "SYSTEMATIQUE")

    def inspecter(self):
        """
        Simule une inspection avec un détecteur imparfait.
        Gère les SCÉNARIOS 2, 3, 5, 6.
        """
        if self.en_panne:
            return # On n'inspecte pas une machine déjà arrêtée

        # La réalité du terrain
        seuil_alerte = self.params.get('seuil_alerte', 15.0)
        anomalie_reelle = (self.usure >= seuil_alerte)

        # Le détecteur (Simulation d'erreur)
        # Probabilité de voir le défaut si présent (Sensibilité)
        prob_detection = self.params.get('prob_detection', 0.9) 
        # Probabilité de voir un défaut si absent (Fausse alarme)
        prob_fausse_alarme = self.params.get('prob_fausse_alarme', 0.05)

        detecteur_sonne = False
        
        if anomalie_reelle:
            # Cas où il y a un problème
            if random.random() < prob_detection:
                detecteur_sonne = True # SCÉNARIO 3 : Vrai Positif
            else:
                detecteur_sonne = False # SCÉNARIO 5 : Faux Négatif (Dangereux !)
        else:
            # Cas où tout va bien
            if random.random() < prob_fausse_alarme:
                detecteur_sonne = True # SCÉNARIO 6 : Faux Positif (Coûteux !)
            else:
                detecteur_sonne = False # SCÉNARIO 2 : Vrai Négatif (RAS)

        # Décision
        if detecteur_sonne:
            self.enregistrer_event("INSPECTION", "Alarme détecteur -> Maintenance requise")
            # Politique : On répare ou on remplace ?
            # Disons : si usure très haute -> Remplacement, sinon Réparation
            if self.usure > 18.0:
                self.maintenir("REMPLACEMENT", "CONDITIONNEL")
            else:
                self.maintenir("REPARATION", "CONDITIONNEL")
        else:
            self.enregistrer_event("INSPECTION", "RAS")

    def maintenir(self, type_action, declencheur):
        """
        Effectue la maintenance.
        Gère le SCÉNARIO 7 (Réparation imparfaite).
        """
        cout = 0
        if type_action == "REMPLACEMENT":
            # Remise à neuf totale
            self.usure = 0.0
            self.en_panne = False
            self.derniere_maintenance = self.temps
            cout = self.params.get('cout_remplacement', 1000)
            self.enregistrer_event("MAINTENANCE", f"Remplacement ({declencheur}) - Coût: {cout}")

        elif type_action == "REPARATION":
            # SCÉNARIO 7 : Réparation imparfaite
            # On enlève seulement une partie de l'usure (ex: 60%)
            facteur_qualite = self.params.get('qualite_reparation', 0.6) 
            usure_avant = self.usure
            self.usure = self.usure * (1 - facteur_qualite)
            self.en_panne = False
            cout = self.params.get('cout_reparation', 300)
            self.enregistrer_event("MAINTENANCE", f"Réparation ({declencheur}) - Usure: {usure_avant:.1f}->{self.usure:.1f}")

    def enregistrer_event(self, type_evt, details):
        self.historique.append({
            "temps": self.temps,
            "type": type_evt,
            "details": details,
            "usure_au_moment": round(self.usure, 2)
        })

# --- Zone de Test rapide (Pour voir si ça marche) ---
if __name__ == "__main__":
    # Paramètres de test
    parametres = {
        'alpha': 0.5, 'seuil_panne': 20.0, 'seuil_alerte': 12.0,
        'prob_detection': 0.9, 'prob_fausse_alarme': 0.1,
        'cout_remplacement': 2000, 'cout_reparation': 500,
        'qualite_reparation': 0.5 # Réparation médiocre
    }

    # Création d'un système
    mon_sys = Systeme("Moteur-01", parametres)
    
    print("--- DÉBUT SIMULATION ---")
    # On simule 50 jours
    for jour in range(1, 51):
        # 1. Le système vit (Scénario 1)
        usage_jour = random.uniform(0.8, 1.2)
        mon_sys.vieillir(usage_jour)
        
        # 2. Si panne (Scénario 4)
        if mon_sys.en_panne:
            print(f"Jour {jour}: 🚨 PANNE ! Usure: {mon_sys.usure:.2f}")
            mon_sys.maintenir("REMPLACEMENT", "PANNE")
        
        # 3. Inspection tous les 10 jours
        elif jour % 10 == 0:
            print(f"Jour {jour}: 🔍 Inspection... (Usure réelle: {mon_sys.usure:.2f})")
            mon_sys.inspecter()
    
    print("\n--- HISTORIQUE DES ÉVÉNEMENTS ---")
    for evt in mon_sys.historique:
        print(f"J{evt['temps']} | {evt['type']} : {evt['details']} (Usure: {evt['usure_au_moment']})")