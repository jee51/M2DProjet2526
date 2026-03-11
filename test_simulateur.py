import csv
import tempfile
import unittest
from pathlib import Path

from evaluation_monte_carlo import lancer_evaluation
from simulateur_asija_gem import (
    ConfigSimulation,
    PolitiqueMaintenance,
    SimulateurMaintenance,
)


class TestSimulateurMaintenance(unittest.TestCase):
    def test_etat_journalier_couvre_tous_les_jours(self):
        config = ConfigSimulation(n_systemes=4, n_jours=30, seed=123, loi_usure="lognormal")
        politique = PolitiqueMaintenance(
            nom="conditionnelle_test",
            inspections_actives=True,
            intervalle_inspection_jours=10,
            seuil_alerte_inspection=1.0,
        )

        simulateur = SimulateurMaintenance(config, politique)
        resume = simulateur.executer()

        self.assertEqual(len(simulateur.data["etat_journalier"]), config.n_systemes * config.n_jours)
        self.assertEqual(resume["n_systemes"], 4)
        self.assertEqual(resume["n_jours"], 30)

    def test_lois_usure_lognormal_et_weibull(self):
        for loi in ["lognormal", "weibull"]:
            with self.subTest(loi=loi):
                config = ConfigSimulation(n_systemes=3, n_jours=20, seed=200, loi_usure=loi)
                politique = PolitiqueMaintenance(nom=f"test_{loi}", inspections_actives=False)
                simulateur = SimulateurMaintenance(config, politique)
                simulateur.executer()

                increments = [row["increment_usure"] for row in simulateur.data["usage_log"]]
                self.assertTrue(increments)
                self.assertTrue(all(valeur >= 0 for valeur in increments))

    def test_maintenance_systematique_declenche_des_actions(self):
        config = ConfigSimulation(n_systemes=5, n_jours=45, seed=456, loi_usure="lognormal")
        politique = PolitiqueMaintenance(
            nom="systematique_court",
            inspections_actives=False,
            remplacement_systematique_jours=12,
        )

        simulateur = SimulateurMaintenance(config, politique)
        resume = simulateur.executer()

        self.assertGreater(resume["nb_maintenances"], 0)
        self.assertTrue(
            any(row["declencheur"] == "SYSTEMATIQUE" for row in simulateur.data["maintenance"])
        )

    def test_monte_carlo_genere_les_fichiers_attendus(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _, synthese = lancer_evaluation(
                repetitions=2,
                n_systemes=8,
                n_jours=40,
                seed_depart=999,
                dossier_sortie=tmpdir,
            )

            dossier = Path(tmpdir)
            self.assertTrue((dossier / "replications.csv").exists())
            self.assertTrue((dossier / "synthese_monte_carlo.csv").exists())
            self.assertEqual(len(synthese), 4)

            with (dossier / "synthese_monte_carlo.csv").open("r", encoding="utf-8") as fichier:
                lignes = list(csv.DictReader(fichier))
            self.assertEqual(len(lignes), 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
