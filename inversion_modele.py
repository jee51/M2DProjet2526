import argparse
import csv
import math
import random
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, pstdev

from simulateur_asija_gem import ConfigSimulation, SimulateurMaintenance, politiques_par_defaut


@dataclass
class ObservedSummary:
    """Résumé des données observées à expliquer par calibration."""

    policy_name: str
    n_systemes: int
    n_jours: int
    usage_log_mu: float
    usage_log_sigma: float
    metrics: dict[str, float]


@dataclass
class CandidateResult:
    """Résultat associé à un jeu de paramètres candidat."""

    params: dict[str, float]
    score: float
    simulated_metrics: dict[str, float]


def read_csv(path: Path) -> list[dict]:
    """Lit un CSV en liste de dictionnaires."""
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, rows: list[dict]) -> None:
    """Écrit une liste de dictionnaires dans un CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def safe_mean(values: list[float]) -> float:
    """Moyenne robuste si la liste est vide."""
    return mean(values) if values else 0.0


def safe_std(values: list[float]) -> float:
    """Écart-type robuste si la liste est trop courte."""
    return pstdev(values) if len(values) > 1 else 0.0


def estimate_usage_lognormal_params(usage_rows: list[dict]) -> tuple[float, float]:
    """Estime les paramètres log-normaux de l'usage observé.

    On travaille sur le logarithme des quantités d'usage positives.
    """
    values = [float(row["quantite"]) for row in usage_rows if float(row["quantite"]) > 0]
    logs = [math.log(value) for value in values]
    return safe_mean(logs), safe_std(logs)


def summarize_dataset(folder: Path) -> ObservedSummary:
    """Résume un dossier de données observées.

    Ici, "observé" signifie : données disponibles pour la calibration.
    Elles peuvent provenir d'un vrai système ou, comme dans notre projet,
    d'un jeu synthétique généré par le simulateur.
    """
    usage_rows = read_csv(folder / "usage_log.csv")
    inspection_rows = read_csv(folder / "inspections.csv")
    maintenance_rows = read_csv(folder / "maintenance.csv")
    failure_rows = read_csv(folder / "pannes.csv")
    state_rows = read_csv(folder / "etat_journalier.csv")
    resume_rows = read_csv(folder / "resume.csv")

    if not resume_rows:
        raise ValueError(f"Aucun résumé trouvé dans {folder}")

    resume = resume_rows[0]
    usage_mu, usage_sigma = estimate_usage_lognormal_params(usage_rows)

    usure_values = [float(row["usure"]) for row in state_rows]
    degraded_flags = [1.0 if float(row["usure"]) >= 1.0 else 0.0 for row in state_rows]
    inspection_scores = [float(row["score"]) for row in inspection_rows]
    failure_costs = [float(row["cout"]) for row in failure_rows]

    metrics = {
        "nb_pannes": float(resume["nb_pannes"]),
        "nb_maintenances": float(resume["nb_maintenances"]),
        "nb_inspections": float(resume["nb_inspections"]),
        "cout_total": float(resume["cout_total"]),
        "cout_pannes": float(resume["cout_pannes"]),
        "disponibilite": float(resume["disponibilite"]),
        "usure_moyenne": safe_mean(usure_values),
        "proportion_degrades": safe_mean(degraded_flags),
        "score_inspection_moyen": safe_mean(inspection_scores),
        "score_inspection_std": safe_std(inspection_scores),
        "cout_panne_moyen": safe_mean(failure_costs),
        "nb_reparations": float(sum(1 for row in maintenance_rows if row.get("type") == "REPARATION")),
        "nb_remplacements": float(sum(1 for row in maintenance_rows if row.get("type") == "REMPLACEMENT")),
    }

    return ObservedSummary(
        policy_name=str(resume.get("politique", folder.name)),
        n_systemes=int(resume["n_systemes"]),
        n_jours=int(resume["n_jours"]),
        usage_log_mu=usage_mu,
        usage_log_sigma=usage_sigma,
        metrics=metrics,
    )


def summarize_simulation(simulateur: SimulateurMaintenance, resume: dict[str, float | int | str]) -> dict[str, float]:
    """Construit, pour une simulation candidate, les mêmes métriques que côté observé."""
    inspection_rows = simulateur.data["inspections"]
    maintenance_rows = simulateur.data["maintenance"]
    failure_rows = simulateur.data["pannes"]
    state_rows = simulateur.data["etat_journalier"]

    usure_values = [float(row["usure"]) for row in state_rows]
    degraded_flags = [1.0 if float(row["usure"]) >= 1.0 else 0.0 for row in state_rows]
    inspection_scores = [float(row["score"]) for row in inspection_rows]
    failure_costs = [float(row["cout"]) for row in failure_rows]

    return {
        "nb_pannes": float(resume["nb_pannes"]),
        "nb_maintenances": float(resume["nb_maintenances"]),
        "nb_inspections": float(resume["nb_inspections"]),
        "cout_total": float(resume["cout_total"]),
        "cout_pannes": float(resume["cout_pannes"]),
        "disponibilite": float(resume["disponibilite"]),
        "usure_moyenne": safe_mean(usure_values),
        "proportion_degrades": safe_mean(degraded_flags),
        "score_inspection_moyen": safe_mean(inspection_scores),
        "score_inspection_std": safe_std(inspection_scores),
        "cout_panne_moyen": safe_mean(failure_costs),
        "nb_reparations": float(sum(1 for row in maintenance_rows if row.get("type") == "REPARATION")),
        "nb_remplacements": float(sum(1 for row in maintenance_rows if row.get("type") == "REMPLACEMENT")),
    }


def objective(observed: dict[str, float], simulated: dict[str, float]) -> float:
    """Fonction objectif de calibration.

    Plus le score est faible, plus les statistiques simulées ressemblent
    aux statistiques observées.
    """
    weights = {
        "nb_pannes": 2.0,
        "nb_maintenances": 1.5,
        "nb_inspections": 1.0,
        "cout_total": 1.5,
        "cout_pannes": 1.5,
        "disponibilite": 2.0,
        "usure_moyenne": 2.0,
        "proportion_degrades": 2.0,
        "score_inspection_moyen": 1.0,
        "score_inspection_std": 1.0,
        "cout_panne_moyen": 1.0,
        "nb_reparations": 1.0,
        "nb_remplacements": 1.0,
    }
    score = 0.0
    for key, weight in weights.items():
        obs = observed.get(key, 0.0)
        sim = simulated.get(key, 0.0)
        scale = max(abs(obs), 1.0)
        score += weight * ((sim - obs) / scale) ** 2
    return score


def policy_from_name(name: str):
    """Retrouve la politique correspondant au nom stocké dans les données observées."""
    for policy in politiques_par_defaut():
        if policy.nom == name:
            return policy
    raise ValueError(f"Politique inconnue: {name}")


def sample_params(rng: random.Random, center: dict[str, float] | None = None, shrink: float = 1.0) -> dict[str, float]:
    """Échantillonne un jeu de paramètres candidat.

    Deux modes sont utilisés :
    - recherche large autour d'intervalles plausibles ;
    - raffinement autour du meilleur candidat courant.
    """
    base = {
        "usure_base": 0.0025,
        "usure_age_facteur": 0.35,
        "lambda_panne_base": 0.00015,
        "lambda_panne_usure": 1.10,
        "lambda_panne_age": 0.20,
        "inspection_noise_std": 0.20,
        "fraction_usure_restante_apres_reparation": 0.30,
    }
    current = center or base

    def around(value: float, low: float, high: float, factor: float) -> float:
        """Tire autour d'une valeur donnée avec une amplitude contrôlée."""
        if center is None:
            return rng.uniform(low, high)
        amplitude = (high - low) * factor * 0.5
        return min(high, max(low, rng.uniform(value - amplitude, value + amplitude)))

    return {
        "usure_base": around(current["usure_base"], 0.0008, 0.0060, shrink),
        "usure_age_facteur": around(current["usure_age_facteur"], 0.05, 1.00, shrink),
        "lambda_panne_base": around(current["lambda_panne_base"], 0.00003, 0.00050, shrink),
        "lambda_panne_usure": around(current["lambda_panne_usure"], 0.20, 2.50, shrink),
        "lambda_panne_age": around(current["lambda_panne_age"], 0.01, 0.60, shrink),
        "inspection_noise_std": around(current["inspection_noise_std"], 0.05, 0.50, shrink),
        "fraction_usure_restante_apres_reparation": around(current["fraction_usure_restante_apres_reparation"], 0.05, 0.70, shrink),
    }


def build_config(observed: ObservedSummary, params: dict[str, float], seed: int) -> ConfigSimulation:
    """Construit une configuration de simulation à partir d'un candidat.

    Les paramètres d'usage sont repris depuis les données observées,
    tandis que les paramètres d'usure, de panne et de détection sont calibrés.
    """
    return ConfigSimulation(
        n_systemes=observed.n_systemes,
        n_jours=observed.n_jours,
        seed=seed,
        usage_log_mu=observed.usage_log_mu,
        usage_log_sigma=observed.usage_log_sigma,
        usure_base=params["usure_base"],
        usure_age_facteur=params["usure_age_facteur"],
        loi_usure="lognormal",
        lambda_panne_base=params["lambda_panne_base"],
        lambda_panne_usure=params["lambda_panne_usure"],
        lambda_panne_age=params["lambda_panne_age"],
        inspection_noise_std=params["inspection_noise_std"],
        fraction_usure_restante_apres_reparation=params["fraction_usure_restante_apres_reparation"],
    )


def evaluate_candidate(observed: ObservedSummary, params: dict[str, float], replications: int, seed: int) -> CandidateResult:
    """Évalue un candidat en relançant le simulateur puis en comparant les métriques."""
    policy = policy_from_name(observed.policy_name)
    metrics_list = []
    for replication in range(replications):
        config = build_config(observed, params, seed + replication)
        simulateur = SimulateurMaintenance(config, policy)
        resume = simulateur.executer()
        metrics_list.append(summarize_simulation(simulateur, resume))

    aggregated = {}
    for key in observed.metrics.keys():
        aggregated[key] = safe_mean([metrics[key] for metrics in metrics_list])

    return CandidateResult(params=params, score=objective(observed.metrics, aggregated), simulated_metrics=aggregated)


def calibrate(folder: Path, broad_trials: int, refine_trials: int, replications: int, seed: int) -> tuple[ObservedSummary, CandidateResult, list[dict]]:
    """Exécute la calibration en deux phases : large puis fine."""
    observed = summarize_dataset(folder)
    rng = random.Random(seed)
    history = []
    best: CandidateResult | None = None

    for stage_name, trials, shrink in [("broad", broad_trials, 1.0), ("refine", refine_trials, 0.20)]:
        for trial in range(trials):
            params = sample_params(rng, center=best.params if best else None, shrink=shrink)
            result = evaluate_candidate(observed, params, replications=replications, seed=seed + 100 * len(history) + trial)
            history.append({
                "stage": stage_name,
                "trial": len(history) + 1,
                "score": round(result.score, 6),
                **{k: round(v, 8) for k, v in result.params.items()},
            })
            if best is None or result.score < best.score:
                best = result

    assert best is not None
    return observed, best, history


def parser() -> argparse.Namespace:
    """Définit les arguments en ligne de commande."""
    ap = argparse.ArgumentParser(description="Aborde le bonus d'inversion du problème par calibration simulation-vers-données.")
    ap.add_argument("--observed-folder", type=str, default="data/conditionnelle_30j", help="Dossier contenant les données observées à expliquer.")
    ap.add_argument("--broad-trials", type=int, default=25, help="Nombre d'essais de recherche large.")
    ap.add_argument("--refine-trials", type=int, default=20, help="Nombre d'essais de raffinement autour du meilleur candidat.")
    ap.add_argument("--replications", type=int, default=1, help="Nombre de réplications par candidat.")
    ap.add_argument("--seed", type=int, default=2026, help="Graine aléatoire pour la calibration.")
    ap.add_argument("--output", type=str, default="data/inversion", help="Dossier de sortie des résultats de calibration.")
    return ap.parse_args()


def main() -> None:
    """Point d'entrée principal du script d'inversion."""
    args = parser()
    observed_folder = Path(args.observed_folder)
    output = Path(args.output)

    observed, best, history = calibrate(
        folder=observed_folder,
        broad_trials=args.broad_trials,
        refine_trials=args.refine_trials,
        replications=args.replications,
        seed=args.seed,
    )

    metrics_rows = []
    for key, observed_value in observed.metrics.items():
        abs_error = abs(best.simulated_metrics[key] - observed_value)
        relative_error = abs_error / max(abs(observed_value), 1e-12)
        metrics_rows.append(
            {
                "metric": key,
                "observed": round(observed_value, 6),
                "simulated_best": round(best.simulated_metrics[key], 6),
                "abs_error": round(abs_error, 6),
                "relative_error": round(relative_error, 6),
            }
        )

    params_rows = [
        {"parameter": "usage_log_mu", "estimated_value": round(observed.usage_log_mu, 6), "method": "direct_from_usage_logs"},
        {"parameter": "usage_log_sigma", "estimated_value": round(observed.usage_log_sigma, 6), "method": "direct_from_usage_logs"},
    ]
    params_rows.extend(
        {"parameter": key, "estimated_value": round(value, 8), "method": "simulation_based_calibration"}
        for key, value in best.params.items()
    )

    write_csv(output / "calibration_history.csv", history)
    write_csv(output / "best_parameters.csv", params_rows)
    write_csv(output / "observed_vs_simulated_best.csv", metrics_rows)

    print("=== Inversion du problème (bonus) ===")
    print(f"Données observées: {observed_folder}")
    print(f"Politique considérée: {observed.policy_name}")
    print("Paramètres estimés:")
    print(f"- usage_log_mu = {observed.usage_log_mu:.4f}")
    print(f"- usage_log_sigma = {observed.usage_log_sigma:.4f}")
    for key, value in best.params.items():
        print(f"- {key} = {value:.6f}")
    print(f"Score de calibration = {best.score:.6f}")
    print(f"Résultats écrits dans {output}")


if __name__ == "__main__":
    main()
