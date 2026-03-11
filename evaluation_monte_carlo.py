import argparse
import csv
import math
from pathlib import Path
from statistics import mean, stdev

from simulateur_asija_gem import ConfigSimulation, SimulateurMaintenance, politiques_par_defaut


def intervalle_confiance_95(valeurs: list[float]) -> tuple[float, float]:
    if not valeurs:
        return 0.0, 0.0
    if len(valeurs) == 1:
        return valeurs[0], valeurs[0]
    moyenne = mean(valeurs)
    ecart_type = stdev(valeurs)
    marge = 1.96 * ecart_type / math.sqrt(len(valeurs))
    return moyenne - marge, moyenne + marge


def ecrire_csv(chemin: Path, lignes: list[dict]) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    if not lignes:
        chemin.write_text("", encoding="utf-8")
        return

    with chemin.open("w", newline="", encoding="utf-8") as fichier:
        writer = csv.DictWriter(fichier, fieldnames=list(lignes[0].keys()))
        writer.writeheader()
        writer.writerows(lignes)


def lancer_evaluation(
    repetitions: int,
    n_systemes: int,
    n_jours: int,
    seed_depart: int,
    dossier_sortie: str,
) -> tuple[list[dict], list[dict]]:
    replicats = []
    resumes = []

    for politique_index, politique in enumerate(politiques_par_defaut()):
        resumes_politique = []
        for repetition in range(repetitions):
            seed = seed_depart + 1000 * politique_index + repetition
            config = ConfigSimulation(
                n_systemes=n_systemes,
                n_jours=n_jours,
                seed=seed,
            )
            simulateur = SimulateurMaintenance(config, politique)
            resume = simulateur.executer()
            resume_replicat = {
                "politique": politique.nom,
                "replication": repetition + 1,
                **resume,
            }
            replicats.append(resume_replicat)
            resumes_politique.append(resume)

        couts = [float(row["cout_total"]) for row in resumes_politique]
        pannes = [float(row["nb_pannes"]) for row in resumes_politique]
        disponibilites = [float(row["disponibilite"]) for row in resumes_politique]

        ic_cout_bas, ic_cout_haut = intervalle_confiance_95(couts)
        ic_panne_bas, ic_panne_haut = intervalle_confiance_95(pannes)
        ic_disp_bas, ic_disp_haut = intervalle_confiance_95(disponibilites)

        resumes.append(
            {
                "politique": politique.nom,
                "repetitions": repetitions,
                "n_systemes": n_systemes,
                "n_jours": n_jours,
                "cout_total_moyen": round(mean(couts), 2),
                "cout_total_ic95_bas": round(ic_cout_bas, 2),
                "cout_total_ic95_haut": round(ic_cout_haut, 2),
                "nb_pannes_moyen": round(mean(pannes), 3),
                "nb_pannes_ic95_bas": round(ic_panne_bas, 3),
                "nb_pannes_ic95_haut": round(ic_panne_haut, 3),
                "disponibilite_moyenne": round(mean(disponibilites), 6),
                "disponibilite_ic95_bas": round(ic_disp_bas, 6),
                "disponibilite_ic95_haut": round(ic_disp_haut, 6),
            }
        )

    racine = Path(dossier_sortie)
    ecrire_csv(racine / "replications.csv", replicats)
    ecrire_csv(racine / "synthese_monte_carlo.csv", resumes)
    return replicats, resumes


def parser_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Évalue les politiques de maintenance par Monte Carlo.")
    parser.add_argument("--repetitions", type=int, default=30, help="Nombre de réplications par politique.")
    parser.add_argument("--n-systemes", type=int, default=200, help="Nombre de systèmes simulés.")
    parser.add_argument("--n-jours", type=int, default=730, help="Durée de simulation en jours.")
    parser.add_argument("--seed", type=int, default=100, help="Graine de départ.")
    parser.add_argument(
        "--output",
        type=str,
        default="data/monte_carlo",
        help="Dossier de sortie des fichiers CSV.",
    )
    return parser.parse_args()


def afficher_synthese(lignes: list[dict]) -> None:
    print("\n=== Synthèse Monte Carlo ===")
    for ligne in sorted(lignes, key=lambda row: float(row["cout_total_moyen"])):
        print(
            f"- {ligne['politique']}: coût moyen={ligne['cout_total_moyen']} €, "
            f"IC95% coût=[{ligne['cout_total_ic95_bas']}, {ligne['cout_total_ic95_haut']}], "
            f"pannes moyennes={ligne['nb_pannes_moyen']}, "
            f"disponibilité moyenne={ligne['disponibilite_moyenne']}"
        )


if __name__ == "__main__":
    args = parser_arguments()
    _, synthese = lancer_evaluation(
        repetitions=args.repetitions,
        n_systemes=args.n_systemes,
        n_jours=args.n_jours,
        seed_depart=args.seed,
        dossier_sortie=args.output,
    )
    afficher_synthese(synthese)
