import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path("data")
OUTPUT = ROOT / "presentation_figures"
OUTPUT.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_bar_chart(labels, values, title, ylabel, filename, color="#4C78A8"):
    plt.figure(figsize=(8, 4.5))
    bars = plt.bar(labels, values, color=color)
    plt.title(title)
    plt.ylabel(ylabel)
    plt.xticks(rotation=15, ha="right")
    plt.grid(axis="y", alpha=0.3)
    for bar, value in zip(bars, values):
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{value:.2f}", ha="center", va="bottom", fontsize=8)
    plt.tight_layout()
    plt.savefig(OUTPUT / filename, dpi=170)
    plt.close()


def save_dual_axis_chart(labels, left_values, right_values, left_label, right_label, title, filename):
    fig, ax1 = plt.subplots(figsize=(8, 4.5))
    ax2 = ax1.twinx()

    x = range(len(labels))
    bars = ax1.bar(x, left_values, color="#F58518", alpha=0.85)
    line = ax2.plot(x, right_values, color="#54A24B", marker="o", linewidth=2)

    ax1.set_xticks(list(x))
    ax1.set_xticklabels(labels, rotation=15, ha="right")
    ax1.set_ylabel(left_label, color="#F58518")
    ax2.set_ylabel(right_label, color="#54A24B")
    ax1.set_title(title)
    ax1.grid(axis="y", alpha=0.3)

    for bar, value in zip(bars, left_values):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{value:.0f}", ha="center", va="bottom", fontsize=8)

    fig.tight_layout()
    fig.savefig(OUTPUT / filename, dpi=170)
    plt.close(fig)


def save_errorbar_chart(labels, means, lowers, uppers, title, ylabel, filename):
    errors = [[m - l for m, l in zip(means, lowers)], [u - m for m, u in zip(means, uppers)]]
    plt.figure(figsize=(8, 4.5))
    plt.errorbar(labels, means, yerr=errors, fmt="o", capsize=5, linewidth=2, color="#E45756")
    plt.title(title)
    plt.ylabel(ylabel)
    plt.xticks(rotation=15, ha="right")
    plt.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUTPUT / filename, dpi=170)
    plt.close()


def save_multi_line_chart(series_by_label, title, ylabel, filename):
    plt.figure(figsize=(8.5, 4.8))
    for label, values in series_by_label.items():
        x = list(range(len(values)))
        plt.plot(x, values, linewidth=2, label=label)
    plt.title(title)
    plt.xlabel("Jour")
    plt.ylabel(ylabel)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT / filename, dpi=170)
    plt.close()


def build_daily_health_series(policy_dir: Path, seuil_defaut: float = 1.0):
    rows = read_csv(policy_dir / "etat_journalier.csv")
    daily = {}
    for row in rows:
        day = row["date"]
        info = daily.setdefault(day, {"count": 0, "degraded": 0, "sum_usure": 0.0})
        usure = float(row["usure"])
        info["count"] += 1
        info["sum_usure"] += usure
        if usure >= seuil_defaut:
            info["degraded"] += 1

    ordered_days = sorted(daily.keys())
    proportion_degraded = []
    mean_usure = []
    for day in ordered_days:
        count = daily[day]["count"]
        proportion_degraded.append(daily[day]["degraded"] / count if count else 0.0)
        mean_usure.append(daily[day]["sum_usure"] / count if count else 0.0)
    return proportion_degraded, mean_usure


def build_cumulative_failures_series(policy_dir: Path):
    rows = read_csv(policy_dir / "pannes.csv")
    daily_failures = {}
    for row in rows:
        day = row["date"]
        daily_failures[day] = daily_failures.get(day, 0) + 1

    state_rows = read_csv(policy_dir / "etat_journalier.csv")
    ordered_days = sorted({row["date"] for row in state_rows})
    cumulative = []
    total = 0
    for day in ordered_days:
        total += daily_failures.get(day, 0)
        cumulative.append(total)
    return cumulative


comparison = read_csv(ROOT / "comparaison_politiques.csv")
comparison_labels = [row["politique"] for row in comparison]
save_bar_chart(
    comparison_labels,
    [float(row["cout_total"]) / 1000.0 for row in comparison],
    title="Comparaison des coûts totaux par politique",
    ylabel="Coût total (k€)",
    filename="couts_politiques.png",
)
save_dual_axis_chart(
    comparison_labels,
    [float(row["nb_pannes"]) for row in comparison],
    [float(row["disponibilite"]) for row in comparison],
    left_label="Nombre de pannes",
    right_label="Disponibilité",
    title="Pannes et disponibilité par politique",
    filename="pannes_disponibilite.png",
)

mc = read_csv(ROOT / "monte_carlo" / "synthese_monte_carlo.csv")
mc_labels = [row["politique"] for row in mc]
save_errorbar_chart(
    mc_labels,
    [float(row["cout_total_moyen"]) / 1000.0 for row in mc],
    [float(row["cout_total_ic95_bas"]) / 1000.0 for row in mc],
    [float(row["cout_total_ic95_haut"]) / 1000.0 for row in mc],
    title="Coût moyen et IC95% par politique",
    ylabel="Coût moyen (k€)",
    filename="monte_carlo_couts.png",
)

ml = read_csv(ROOT / "ml_metrics" / "classification_metrics.csv")
ml_labels = [row["politique"] for row in ml]
save_bar_chart(
    ml_labels,
    [float(row["roc_auc"]) for row in ml],
    title="ROC AUC du détecteur par politique inspectée",
    ylabel="ROC AUC",
    filename="roc_auc_policies.png",
    color="#72B7B2",
)

health_series = {}
wear_series = {}
failure_series = {}
for policy_name in ["corrective_pure", "conditionnelle_30j", "systematique_200j", "mixte_30j_plus_200j"]:
    policy_dir = ROOT / policy_name
    if policy_dir.exists():
        degraded, mean_wear = build_daily_health_series(policy_dir, seuil_defaut=1.0)
        health_series[policy_name] = degraded
        wear_series[policy_name] = mean_wear
        failure_series[policy_name] = build_cumulative_failures_series(policy_dir)

save_multi_line_chart(
    health_series,
    title="Proportion de systèmes dégradés au cours du temps",
    ylabel="Proportion avec usure ≥ seuil défaut",
    filename="proportion_systemes_degrades.png",
)

save_multi_line_chart(
    wear_series,
    title="Usure moyenne de la flotte au cours du temps",
    ylabel="Usure moyenne",
    filename="usure_moyenne_flotte.png",
)

save_multi_line_chart(
    failure_series,
    title="Nombre cumulé de pannes au cours du temps",
    ylabel="Pannes cumulées",
    filename="pannes_cumulees_temps.png",
)

print("Figures de présentation générées dans data/presentation_figures/")
