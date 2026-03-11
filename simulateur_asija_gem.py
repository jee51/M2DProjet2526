import csv
import math
import os
import random
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path


# ---------------------------------------------------------
# 1. CONFIGURATION
# ---------------------------------------------------------
@dataclass(frozen=True)
class ConfigSimulation:
    """Paramètres globaux du simulateur.

    Ils ne proviennent pas d'un calibrage sur données réelles.
    Ils ont été choisis pour obtenir un modèle :
    - stochastique,
    - numériquement stable,
    - capable de différencier clairement les politiques de maintenance.
    """

    n_systemes: int = 200  # Nombre de systèmes simulés dans la flotte
    n_jours: int = 730  # Horizon temporel de simulation en jours
    seed: int = 42  #pour rendre les simulations reproductibles
    date_debut: str = "2026-01-01"  # Date de démarrage de la simulation

    # Usage et usure
    usage_log_mu: float = 1.0  # Paramètre mu de la loi log-normale d'usage journalier
    usage_log_sigma: float = 0.45  # Dispersion de l'usage journalier autour de sa moyenne
    usure_base: float = 0.0025  # Taux de base reliant usage et incrément d'usure
    usure_age_facteur: float = 0.35  # Accélération de l'usure liée au vieillissement du composant
    loi_usure: str = "lognormal"  # Loi retenue pour l'incrément d'usure: lognormal, weibull ou gamma
    usure_log_sigma: float = 0.55  # Dispersion log-normale de l'incrément d'usure
    usure_weibull_shape: float = 1.8  # Paramètre de forme si l'on choisit une loi Weibull
    usure_dispersion: float = 6.0  # Paramètre de dispersion si l'on utilise la loi Gamma par défaut de secours

    # Détection / inspection
    inspection_noise_std: float = 0.20  # Écart-type du bruit ajouté au score d'inspection
    seuil_defaut: float = 1.00  # Niveau d'usure à partir duquel on considère un vrai défaut
    seuil_remplacement: float = 1.50  # Niveau d'usure au-delà duquel on remplace plutôt qu'on répare
    delai_inspection_sigma: float = 4.0  # Variabilité autour de l'intervalle théorique entre inspections

    # Panne : modèle par risque journalier
    lambda_panne_base: float = 0.00015  # Intensité de panne minimale quand le composant est peu dégradé
    lambda_panne_usure: float = 1.10  # Sensibilité du risque de panne à l'usure courante
    lambda_panne_age: float = 0.20  # Sensibilité du risque de panne à l'âge du composant
    max_exponent: float = 8.0  # Borne numérique pour éviter une explosion de l'exponentielle

    # Maintenance et coûts
    cout_inspection: float = 60.0  # Coût unitaire d'une inspection
    cout_reparation: float = 500.0  # Coût unitaire d'une réparation
    cout_remplacement: float = 1800.0  # Coût unitaire d'un remplacement préventif ou correctif
    cout_panne_fixe: float = 4000.0  # Coût fixe subi dès qu'une panne survient
    cout_panne_par_usure: float = 1200.0  # Surcoût de panne lié au niveau d'usure atteint
    cout_panne_par_jour_arret: float = 800.0  # Coût d'immobilisation par jour d'arrêt
    duree_reparation_jours: int = 2  # Durée d'indisponibilité causée par une réparation
    duree_remplacement_jours: int = 4  # Durée d'indisponibilité causée par un remplacement
    fraction_usure_restante_apres_reparation: float = 0.30  # Part d'usure conservée après une réparation partielle


@dataclass(frozen=True)
class PolitiqueMaintenance:
    """Définit une politique de maintenance à comparer.

    Une politique combine éventuellement :
    - des inspections périodiques,
    - un seuil d'alerte,
    - un remplacement systématique à âge fixe.
    """

    nom: str  # Nom  de la politique
    inspections_actives: bool  # Indique si la politique prévoit des inspections périodiques
    intervalle_inspection_jours: int | None = None  # Intervalle moyen entre deux inspections si elles sont activées
    seuil_alerte_inspection: float | None = None  # Seuil de score à partir duquel une alerte est déclenchée
    remplacement_systematique_jours: int | None = None  # Âge auquel on remplace automatiquement le composant


@dataclass
class EtatActif:
    """État courant du composant monté sur un système.

    Cet objet porte l'état minimal nécessaire pour faire évoluer
    un composant jour après jour dans la simulation.
    """

    systeme_id: str  # Identifiant du système porteur du composant
    asset_id: str  # Identifiant du composant actuellement installé
    date_installation: date  # Date de pose du composant actuel
    usure: float  # Niveau d'usure courant du composant
    prochain_controle: date | None  # Date prévue pour la prochaine inspection, si applicable
    indisponible_jusqu_au: date  # Date jusqu'à laquelle le système reste immobilisé après maintenance ou panne


# ---------------------------------------------------------
# 2. SIMULATEUR
# ---------------------------------------------------------
class SimulateurMaintenance:
    def __init__(self, config: ConfigSimulation, politique: PolitiqueMaintenance):
        """Construit un simulateur pour une politique donnée."""
        self.config = config
        self.politique = politique
        self.rng = random.Random(config.seed)
        self.date_debut = datetime.strptime(config.date_debut, "%Y-%m-%d").date()
        self.data = {
            "assets": [],
            "usage_log": [],
            "inspections": [],
            "maintenance": [],
            "pannes": [],
            "etat_journalier": [],
        }

    def generer_id(self, prefixe: str) -> str:
        """Génère un identifiant court pour les tables exportées."""
        return f"{prefixe}_{uuid.uuid4().hex[:8].upper()}"

    def _tirer_delai_inspection(self) -> int:
        """Tire un délai d'inspection autour de l'intervalle nominal.

        On évite un calendrier trop rigide en ajoutant une variabilité gaussienne.
        """
        intervalle = self.politique.intervalle_inspection_jours
        if intervalle is None:
            raise ValueError("La politique ne définit pas d'intervalle d'inspection.")
        jours = int(round(self.rng.gauss(intervalle, self.config.delai_inspection_sigma)))
        return max(1, jours)

    def _tirer_usage(self) -> float:
        """Tire un niveau d'usage journalier strictement positif.

        La loi log-normale est choisie car elle produit beaucoup de jours ordinaires
        et quelques jours plus chargés, ce qui est plausible dans un contexte opérationnel.
        """
        return self.rng.lognormvariate(self.config.usage_log_mu, self.config.usage_log_sigma)

    def _increment_usure(self, usage: float, age_jours: int) -> float:
        """Calcule l'incrément d'usure quotidien.

        La moyenne augmente avec :
        - l'usage du jour,
        - l'âge du composant.

        La loi utilisée peut être log-normale, Weibull ou Gamma selon la configuration.
        """
        age_annees = age_jours / 365.0
        moyenne = self.config.usure_base * usage * (1.0 + self.config.usure_age_facteur * age_annees)
        moyenne = max(1e-8, moyenne)

        if self.config.loi_usure == "lognormal":
            sigma = max(1e-6, self.config.usure_log_sigma)
            mu = math.log(moyenne) - 0.5 * sigma * sigma
            return self.rng.lognormvariate(mu, sigma)

        if self.config.loi_usure == "weibull":
            shape = max(1e-6, self.config.usure_weibull_shape)
            echelle = moyenne / math.gamma(1.0 + 1.0 / shape)
            echelle = max(1e-8, echelle)
            return echelle * self.rng.weibullvariate(1.0, shape)

        shape = max(1e-3, self.config.usure_dispersion)
        scale = moyenne / shape
        return self.rng.gammavariate(shape, scale)

    def _probabilite_panne_journaliere(self, usure: float, age_jours: int) -> float:
        """Transforme l'état du composant en probabilité journalière de panne.

        Plus l'usure et l'âge augmentent, plus la probabilité de panne croît.
        On passe par une intensité exponentielle, puis on la convertit en probabilité.
        """
        age_annees = age_jours / 365.0
        exposant = self.config.lambda_panne_usure * usure + self.config.lambda_panne_age * age_annees
        exposant = max(-self.config.max_exponent, min(self.config.max_exponent, exposant))
        intensite = self.config.lambda_panne_base * math.exp(exposant)
        return 1.0 - math.exp(-intensite)

    def _cout_panne(self, usure: float, duree_arret: int) -> float:
        """Calcule le coût d'une panne.

        Le coût comprend :
        - une part fixe,
        - une part liée à l'usure au moment de la panne,
        - une part liée au temps d'arrêt.
        """
        return (
            self.config.cout_panne_fixe
            + self.config.cout_panne_par_usure * usure
            + self.config.cout_panne_par_jour_arret * duree_arret
        )

    def _initialiser_etat(self, index_systeme: int) -> EtatActif:
        """Crée l'état initial d'un système et de son premier composant."""
        systeme_id = f"SYS_{index_systeme:03d}"
        asset_id = self.generer_id("AST")
        prochain_controle = None
        if self.politique.inspections_actives:
            prochain_controle = self.date_debut + timedelta(days=self._tirer_delai_inspection())

        self.data["assets"].append(
            {
                "asset_id": asset_id,
                "systeme_id": systeme_id,
                "date_installation": self.date_debut.isoformat(),
                "politique": self.politique.nom,
            }
        )
        return EtatActif(
            systeme_id=systeme_id,
            asset_id=asset_id,
            date_installation=self.date_debut,
            usure=0.0,
            prochain_controle=prochain_controle,
            indisponible_jusqu_au=self.date_debut,
        )

    def _enregistrer_etat_journalier(
        self,
        courant: date,
        etat: EtatActif,
        disponible: bool,
        usage: float,
        evenement: str,
    ) -> None:
        """Ajoute une ligne dans le journal quotidien du système."""
        age_jours = (courant - etat.date_installation).days
        self.data["etat_journalier"].append(
            {
                "date": courant.isoformat(),
                "systeme_id": etat.systeme_id,
                "asset_id": etat.asset_id,
                "age_jours": age_jours,
                "usure": round(etat.usure, 6),
                "disponible": int(disponible),
                "usage": round(usage, 6),
                "evenement": evenement,
            }
        )

    def _effectuer_inspection(self, courant: date, etat: EtatActif) -> bool:
        """Effectue une inspection et déclenche éventuellement une maintenance.

        Le score observé est bruité : on ne mesure pas exactement l'usure réelle.
        """
        score = etat.usure + self.rng.gauss(0.0, self.config.inspection_noise_std)
        vrai_defaut = etat.usure >= self.config.seuil_defaut
        alerte = bool(score >= (self.politique.seuil_alerte_inspection or self.config.seuil_defaut))

        self.data["inspections"].append(
            {
                "id": self.generer_id("INSP"),
                "date": courant.isoformat(),
                "systeme_id": etat.systeme_id,
                "asset_id": etat.asset_id,
                "score": round(score, 6),
                "vrai_defaut": int(vrai_defaut),
                "alerte": int(alerte),
                "cout": self.config.cout_inspection,
            }
        )

        etat.prochain_controle = courant + timedelta(days=self._tirer_delai_inspection())

        if not alerte:
            return False

        type_acte = "REMPLACEMENT" if etat.usure >= self.config.seuil_remplacement else "REPARATION"
        self._appliquer_maintenance(courant, etat, type_acte, "INSPECTION")
        return True

    def _appliquer_maintenance(
        self,
        courant: date,
        etat: EtatActif,
        type_acte: str,
        declencheur: str,
    ) -> None:
        """Applique une réparation ou un remplacement.

        - une réparation réduit l'usure sans remettre à neuf ;
        - un remplacement réinstalle un composant neuf.
        """
        if type_acte == "REPARATION":
            duree = self.config.duree_reparation_jours
            cout = self.config.cout_reparation
        else:
            duree = self.config.duree_remplacement_jours
            cout = self.config.cout_remplacement

        self.data["maintenance"].append(
            {
                "id": self.generer_id("ACT"),
                "date": courant.isoformat(),
                "systeme_id": etat.systeme_id,
                "asset_id": etat.asset_id,
                "type": type_acte,
                "declencheur": declencheur,
                "cout": cout,
            }
        )

        if type_acte == "REMPLACEMENT":
            nouvel_asset_id = self.generer_id("AST")
            self.data["assets"].append(
                {
                    "asset_id": nouvel_asset_id,
                    "systeme_id": etat.systeme_id,
                    "date_installation": courant.isoformat(),
                    "politique": self.politique.nom,
                }
            )
            etat.asset_id = nouvel_asset_id
            etat.usure = 0.0
            etat.date_installation = courant
        else:
            etat.usure *= self.config.fraction_usure_restante_apres_reparation

        if self.politique.inspections_actives:
            etat.prochain_controle = courant + timedelta(days=self._tirer_delai_inspection())
        else:
            etat.prochain_controle = None
        etat.indisponible_jusqu_au = courant + timedelta(days=duree)

    def executer(self) -> dict[str, float | int | str]:
        """Boucle principale de simulation.

        Pour chaque jour et pour chaque système, on applique successivement :
        1. indisponibilité éventuelle,
        2. maintenance systématique éventuelle,
        3. inspection éventuelle,
        4. usage du jour,
        5. incrément d'usure,
        6. tirage de panne,
        7. enregistrement de l'état du jour.
        """
        print(f"\n=== Simulation : {self.politique.nom} ===")
        etats = [self._initialiser_etat(i) for i in range(self.config.n_systemes)]

        for jour in range(self.config.n_jours):
            courant = self.date_debut + timedelta(days=jour)

            for etat in etats:
                if courant < etat.indisponible_jusqu_au:
                    self._enregistrer_etat_journalier(courant, etat, False, 0.0, "INDISPONIBLE")
                    continue

                age_jours = (courant - etat.date_installation).days

                if (
                    self.politique.remplacement_systematique_jours is not None
                    and age_jours >= self.politique.remplacement_systematique_jours
                ):
                    self._appliquer_maintenance(courant, etat, "REMPLACEMENT", "SYSTEMATIQUE")
                    self._enregistrer_etat_journalier(courant, etat, False, 0.0, "MAINTENANCE_SYSTEMATIQUE")
                    continue

                if (
                    self.politique.inspections_actives
                    and etat.prochain_controle is not None
                    and courant >= etat.prochain_controle
                ):
                    maintenance_declenchee = self._effectuer_inspection(courant, etat)
                    if maintenance_declenchee:
                        self._enregistrer_etat_journalier(courant, etat, False, 0.0, "INSPECTION_MAINTENANCE")
                        continue

                usage = self._tirer_usage()
                inc_usure = self._increment_usure(usage, age_jours)
                etat.usure += inc_usure

                self.data["usage_log"].append(
                    {
                        "date": courant.isoformat(),
                        "systeme_id": etat.systeme_id,
                        "asset_id": etat.asset_id,
                        "quantite": round(usage, 6),
                        "increment_usure": round(inc_usure, 6),
                    }
                )

                # On calcule d'abord la probabilité de panne du jour à partir
                # de l'état courant du composant.
                proba_panne = self._probabilite_panne_journaliere(etat.usure, age_jours)

                # Puis on fait un tirage uniforme entre 0 et 1.
                # Si le tirage est inférieur à la probabilité, on considère
                # que la panne se produit effectivement aujourd'hui.
                if self.rng.random() < proba_panne:
                    duree_arret = self.config.duree_remplacement_jours
                    cout_panne = self._cout_panne(etat.usure, duree_arret)
                    self.data["pannes"].append(
                        {
                            "id": self.generer_id("FAIL"),
                            "date": courant.isoformat(),
                            "systeme_id": etat.systeme_id,
                            "asset_id": etat.asset_id,
                            "usure": round(etat.usure, 6),
                            "probabilite_journaliere": round(proba_panne, 8),
                            "cout": round(cout_panne, 2),
                        }
                    )
                    self._appliquer_maintenance(courant, etat, "REMPLACEMENT", "PANNE")
                    self._enregistrer_etat_journalier(courant, etat, False, usage, "PANNE")
                    continue

                self._enregistrer_etat_journalier(courant, etat, True, usage, "EXPLOITATION")

        return self._construire_resume()

    def _construire_resume(self) -> dict[str, float | int | str]:
        """Construit les indicateurs agrégés de fin de simulation."""
        inspections = self.data["inspections"]
        maintenances = self.data["maintenance"]
        pannes = self.data["pannes"]
        etats = self.data["etat_journalier"]

        cout_inspections = sum(float(row["cout"]) for row in inspections)
        cout_maintenance = sum(float(row["cout"]) for row in maintenances)
        cout_pannes = sum(float(row["cout"]) for row in pannes)
        total_cost = cout_inspections + cout_maintenance + cout_pannes

        jours_disponibles = sum(int(row["disponible"]) for row in etats)
        disponibilite = jours_disponibles / (self.config.n_systemes * self.config.n_jours)

        vrais_positifs = sum(1 for row in inspections if row["vrai_defaut"] == 1 and row["alerte"] == 1)
        faux_negatifs = sum(1 for row in inspections if row["vrai_defaut"] == 1 and row["alerte"] == 0)
        vrais_negatifs = sum(1 for row in inspections if row["vrai_defaut"] == 0 and row["alerte"] == 0)
        faux_positifs = sum(1 for row in inspections if row["vrai_defaut"] == 0 and row["alerte"] == 1)

        sensibilite_empirique = 0.0
        if vrais_positifs + faux_negatifs > 0:
            sensibilite_empirique = vrais_positifs / (vrais_positifs + faux_negatifs)

        specificite_empirique = 0.0
        if vrais_negatifs + faux_positifs > 0:
            specificite_empirique = vrais_negatifs / (vrais_negatifs + faux_positifs)

        return {
            "politique": self.politique.nom,
            "n_systemes": self.config.n_systemes,
            "n_jours": self.config.n_jours,
            "nb_inspections": len(inspections),
            "nb_maintenances": len(maintenances),
            "nb_pannes": len(pannes),
            "cout_inspections": round(cout_inspections, 2),
            "cout_maintenance": round(cout_maintenance, 2),
            "cout_pannes": round(cout_pannes, 2),
            "cout_total": round(total_cost, 2),
            "disponibilite": round(disponibilite, 6),
            "sensibilite_empirique": round(sensibilite_empirique, 6),
            "specificite_empirique": round(specificite_empirique, 6),
        }

    def sauvegarder(self, dossier_sortie: Path, resume: dict[str, float | int | str]) -> None:
        """Écrit les tables et le résumé dans le dossier de sortie."""
        dossier_sortie.mkdir(parents=True, exist_ok=True)
        for table, rows in self.data.items():
            self._ecrire_csv(dossier_sortie / f"{table}.csv", rows)
        self._ecrire_csv(dossier_sortie / "resume.csv", [resume])

    @staticmethod
    def _ecrire_csv(chemin: Path, rows: list[dict]) -> None:
        """Fonction utilitaire d'écriture CSV."""
        if not rows:
            chemin.write_text("", encoding="utf-8")
            return

        with chemin.open("w", newline="", encoding="utf-8") as fichier:
            writer = csv.DictWriter(fichier, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)


# ---------------------------------------------------------
# 3. COMPARAISON DE POLITIQUES
# ---------------------------------------------------------
def politiques_par_defaut() -> list[PolitiqueMaintenance]:
    """Déclare les politiques testées dans le projet."""
    return [
        PolitiqueMaintenance(
            nom="corrective_pure",
            inspections_actives=False,
        ),
        PolitiqueMaintenance(
            nom="conditionnelle_30j",
            inspections_actives=True,
            intervalle_inspection_jours=30,
            seuil_alerte_inspection=1.00,
        ),
        PolitiqueMaintenance(
            nom="systematique_200j",
            inspections_actives=False,
            remplacement_systematique_jours=200,
        ),
        PolitiqueMaintenance(
            nom="mixte_30j_plus_200j",
            inspections_actives=True,
            intervalle_inspection_jours=30,
            seuil_alerte_inspection=1.00,
            remplacement_systematique_jours=200,
        ),
    ]


def slugifier(nom: str) -> str:
    """Convertit un nom de politique en nom de dossier simple."""
    propre = []
    for caractere in nom.lower():
        propre.append(caractere if caractere.isalnum() else "_")
    resultat = "".join(propre)
    while "__" in resultat:
        resultat = resultat.replace("__", "_")
    return resultat.strip("_")


def executer_comparaison(config: ConfigSimulation, dossier_racine: str = "data") -> list[dict[str, float | int | str]]:
    """Exécute successivement toutes les politiques et exporte les résultats."""
    resultats = []
    racine = Path(dossier_racine)
    racine.mkdir(parents=True, exist_ok=True)

    for index, politique in enumerate(politiques_par_defaut()):
        cfg_politique = ConfigSimulation(**{**config.__dict__, "seed": config.seed + index})
        simulateur = SimulateurMaintenance(cfg_politique, politique)
        resume = simulateur.executer()
        simulateur.sauvegarder(racine / slugifier(politique.nom), resume)
        resultats.append(resume)

    SimulateurMaintenance._ecrire_csv(racine / "comparaison_politiques.csv", resultats)
    return resultats


def afficher_resultats(resultats: list[dict[str, float | int | str]]) -> None:
    """Affiche un résumé trié par coût total croissant."""
    print("\n=== Résumé comparatif ===")
    for ligne in sorted(resultats, key=lambda row: float(row["cout_total"])):
        print(
            f"- {ligne['politique']}: "
            f"coût total={ligne['cout_total']} €, "
            f"pannes={ligne['nb_pannes']}, "
            f"maintenances={ligne['nb_maintenances']}, "
            f"disponibilité={ligne['disponibilite']}"
        )


if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    configuration = ConfigSimulation()
    resultats = executer_comparaison(configuration, dossier_racine="data")
    afficher_resultats(resultats)