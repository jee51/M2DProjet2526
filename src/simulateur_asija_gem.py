import os
import math
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

# ---------------------------------------------------------
# 1. CONFIGURATION DU SIMULATEUR
# ---------------------------------------------------------
@dataclass
class ConfigAsija:
    """Parametres du simulateur pour ajuster le comportement et les couts."""
    n_systemes: int = 200        # Nombre de machines
    n_jours: int = 730           # Duree de simulation (jours)
    
    # Physique
    usure_moyenne: float = 0.003 # Vitesse de base d'usure
    accel_age: float = 0.0008    # Acceleration de l'usure avec l'age
    
    # Détecteur
    sensibilite: float = 0.85    # Proba de detecter un vrai defaut
    specificite: float = 0.90    # Proba de ne pas faire de fausse alerte
    score_bruit: float = 0.20    # Bruit sur la mesure d'inspection
    frequence_insp: int = 30     # Jours entre inspections
    
    # Coûts (€)
    cout_reparation: float = 500.0     # Cout d'une reparation
    cout_remplacement: float = 1800.0 # Cout d'un remplacement
    cout_panne: float = 4000.0         # Cout d'arret suite a panne
    
    # Maintenance Systématique
    remplacement_auto_jours: int = 200 # Remplacement systematique

    # Parametres numeriques
    random_seed: int = 42              # Graine aleatoire pour reproductibilite
    max_exponent: float = 100.0        # Seuil de saturation de l'exponentielle
    score_min: float | None = None     # Borne basse du score (None = pas de borne)

# ---------------------------------------------------------
# 2. LOGIQUE DE SIMULATION
# ---------------------------------------------------------
class SimulateurAsija:
    def __init__(self, cfg: ConfigAsija):
        """Initialise le simulateur et ses structures de donnees."""
        self.cfg = cfg
        # Utilisation exclusive de numpy pour l'aléatoire 
        self.rng = np.random.default_rng(self.cfg.random_seed)
        self.start_date = datetime(2026, 1, 1)
        
        self.data = {
            "assets": [], "usage_log": [], "inspections": [],
            "maintenance": [], "pannes": []
        }

    def generer_id(self, prefix):
        """Genere un identifiant court et unique par type d'objet."""
        return f"{prefix}_{uuid.uuid4().hex[:6].upper()}"

    def executer(self):
        """Lance la simulation complete et alimente les tables de sortie."""
        print(f"🚀 Simulation lancée pour {self.cfg.n_systemes} systèmes ...")
        
        for i in range(self.cfg.n_systemes):
            sys_id = f"SYS_{i:03d}"
            asset_id = self.generer_id("AST")
            
            etat = {
                "asset_id": asset_id,
                "usure": 0.0,
                "install_date": self.start_date,
                "busy_until": self.start_date,
                "next_insp": self.start_date + timedelta(days=self.cfg.frequence_insp)
            }
            
            self.data["assets"].append({
                "asset_id": asset_id, "systeme_id": sys_id, 
                "date_installation": self.start_date.date()
            })

            for d in range(self.cfg.n_jours):
                courant = self.start_date + timedelta(days=d)
                
                # Si le système est en maintenance, on saute la journée
                if courant < etat["busy_until"]:
                    continue 

                # SCÉNARIO 8 : Remplacement systématique
                age = (courant - etat["install_date"]).days
                if age >= self.cfg.remplacement_auto_jours:
                    self.appliquer_maintenance(courant, sys_id, etat, "REMPLACEMENT", "SYSTEMATIQUE")
                    continue # FIX: On arrête la journée ici !

                # 1. USAGE ET USURE
                usage = self.rng.lognormal(1.2, 0.6)
                self.data["usage_log"].append({
                    "systeme_id": sys_id, "asset_id": etat["asset_id"],
                    "date": courant.date(), "quantite": usage
                })
                
                moyenne_inc = self.cfg.usure_moyenne * usage * (1.0 + self.cfg.accel_age * age)
                inc_usure = self.rng.gamma(4.0, moyenne_inc / 4.0)
                etat["usure"] += inc_usure

                # 2. INSPECTION
                maintenance_faite_aujourdhui = False # Flag pour éviter le double événement
                
                if courant.date() >= etat["next_insp"].date():
                    score_mesure = float(etat["usure"] + self.rng.normal(0, self.cfg.score_bruit))
                    if self.cfg.score_min is not None:
                        score_mesure = max(self.cfg.score_min, score_mesure)
                    vrai_defaut = (etat["usure"] >= 1.0)
                    
                    if vrai_defaut:
                        detecte = (self.rng.random() < self.cfg.sensibilite) 
                    else:
                        detecte = (self.rng.random() > self.cfg.specificite) 
                    
                    self.data["inspections"].append({
                        "id": self.generer_id("INSP"), "asset_id": etat["asset_id"],
                        "date": courant.date(), "score": score_mesure, "detecte": int(detecte)
                    })
                    
                    etat["next_insp"] = courant + timedelta(days=self.cfg.frequence_insp)
                    
                    if detecte:
                        type_acte = "REMPLACEMENT" if etat["usure"] > 1.5 else "REPARATION"
                        self.appliquer_maintenance(courant, sys_id, etat, type_acte, "INSPECTION")
                        maintenance_faite_aujourdhui = True # On note qu'on a agi

                # FIX: Si on a fait une maintenance, on ne teste pas la panne le même jour
                if maintenance_faite_aujourdhui:
                    continue 

                # 3. PANNE ALÉATOIRE
                # FIX: Sécurisation mathématique de l'exponentielle (Overflow)
                exponent = 2.5 * etat["usure"]
                if exponent > self.cfg.max_exponent: 
                    p_panne = 1.0 # Saturation à 100% si usure extrême
                else:
                    p_panne = 1.0 - math.exp(-0.001 * math.exp(exponent))
                
                if self.rng.random() < p_panne:
                    self.data["pannes"].append({
                        "id": self.generer_id("FAIL"), "asset_id": etat["asset_id"],
                        "date": courant.date(), "cout": self.cfg.cout_panne
                    })
                    self.appliquer_maintenance(courant, sys_id, etat, "REMPLACEMENT", "PANNE")

        self.sauvegarder()

    def appliquer_maintenance(self, date, sys_id, etat, type_acte, declencheur):
        """Applique une action de maintenance et met a jour l'etat de l'actif."""
        duree = 2 if type_acte == "REPARATION" else 4
        cout = self.cfg.cout_reparation if type_acte == "REPARATION" else self.cfg.cout_remplacement
        
        self.data["maintenance"].append({
            "id": self.generer_id("ACT"), "asset_id": etat["asset_id"],
            "date": date.date(), "type": type_acte, "declencheur": declencheur, "cout": cout
        })
        
        if type_acte == "REMPLACEMENT":
            nouveau_id = self.generer_id("AST")
            self.data["assets"].append({
                "asset_id": nouveau_id, "systeme_id": sys_id, "date_installation": date.date()
            })
            etat.update({"asset_id": nouveau_id, "usure": 0.0, "install_date": date})
        else:
            etat["usure"] = etat["usure"] * 0.3
            
        etat["busy_until"] = date + timedelta(days=duree)

    def sauvegarder(self):
        """Ecrit les tables de simulation en CSV dans le dossier data."""
        os.makedirs("data", exist_ok=True)
        for table, rows in self.data.items():
            pd.DataFrame(rows).to_csv(f"data/{table}.csv", index=False)
        print(f"✅ Simulation terminée. Fichiers enregistrés dans le dossier 'data/'.")

if __name__ == "__main__":
    config = ConfigAsija()
    sim = SimulateurAsija(config)
    sim.executer()