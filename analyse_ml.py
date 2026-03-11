import csv
from pathlib import Path
from typing import Iterable

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path("data")
OUTPUT_ROOT = ROOT / "ml_metrics"


def lire_inspections(chemin: Path) -> list[dict]:
    with chemin.open("r", encoding="utf-8") as fichier:
        return list(csv.DictReader(fichier))


def confusion_at_threshold(rows: list[dict], threshold: float) -> tuple[int, int, int, int]:
    tp = fp = tn = fn = 0
    for row in rows:
        y_true = int(row["vrai_defaut"])
        y_pred = 1 if float(row["score"]) >= threshold else 0
        if y_true == 1 and y_pred == 1:
            tp += 1
        elif y_true == 0 and y_pred == 1:
            fp += 1
        elif y_true == 0 and y_pred == 0:
            tn += 1
        else:
            fn += 1
    return tp, fp, tn, fn


def precision(tp: int, fp: int) -> float:
    return tp / (tp + fp) if tp + fp > 0 else 1.0


def recall(tp: int, fn: int) -> float:
    return tp / (tp + fn) if tp + fn > 0 else 0.0


def specificity(tn: int, fp: int) -> float:
    return tn / (tn + fp) if tn + fp > 0 else 0.0


def fpr(fp: int, tn: int) -> float:
    return fp / (fp + tn) if fp + tn > 0 else 0.0


def f1_score(p: float, r: float) -> float:
    return 2 * p * r / (p + r) if p + r > 0 else 0.0


def accuracy(tp: int, fp: int, tn: int, fn: int) -> float:
    total = tp + fp + tn + fn
    return (tp + tn) / total if total > 0 else 0.0


def balanced_accuracy(tpr: float, tnr: float) -> float:
    return 0.5 * (tpr + tnr)


def auc_from_points(points: list[tuple[float, float]]) -> float:
    if len(points) < 2:
        return 0.0
    area = 0.0
    for (x1, y1), (x2, y2) in zip(points[:-1], points[1:]):
        area += (x2 - x1) * (y1 + y2) * 0.5
    return area


def build_roc_points(rows: list[dict]) -> list[dict]:
    sorted_rows = sorted(
        ((float(row["score"]), int(row["vrai_defaut"])) for row in rows),
        key=lambda item: item[0],
        reverse=True,
    )
    total_pos = sum(label for _, label in sorted_rows)
    total_neg = len(sorted_rows) - total_pos

    tp = 0
    fp_count = 0
    points = [{"threshold": float("inf"), "tpr": 0.0, "fpr": 0.0}]
    index = 0
    while index < len(sorted_rows):
        threshold = sorted_rows[index][0]
        while index < len(sorted_rows) and sorted_rows[index][0] == threshold:
            _, label = sorted_rows[index]
            if label == 1:
                tp += 1
            else:
                fp_count += 1
            index += 1
        fn = total_pos - tp
        tn = total_neg - fp_count
        points.append(
            {
                "threshold": threshold,
                "tpr": recall(tp, fn),
                "fpr": fpr(fp_count, tn),
            }
        )

    points.append({"threshold": float("-inf"), "tpr": 1.0, "fpr": 1.0})
    points.sort(key=lambda row: (row["fpr"], row["tpr"]))
    return points


def build_pr_points(rows: list[dict]) -> list[dict]:
    sorted_rows = sorted(
        ((float(row["score"]), int(row["vrai_defaut"])) for row in rows),
        key=lambda item: item[0],
        reverse=True,
    )
    total_pos = sum(label for _, label in sorted_rows)

    tp = 0
    fp_count = 0
    points = [{"threshold": float("inf"), "precision": 1.0, "recall": 0.0}]
    index = 0
    while index < len(sorted_rows):
        threshold = sorted_rows[index][0]
        while index < len(sorted_rows) and sorted_rows[index][0] == threshold:
            _, label = sorted_rows[index]
            if label == 1:
                tp += 1
            else:
                fp_count += 1
            index += 1
        fn = total_pos - tp
        points.append(
            {
                "threshold": threshold,
                "precision": precision(tp, fp_count),
                "recall": recall(tp, fn),
            }
        )

    points.sort(key=lambda row: (row["recall"], row["precision"]))
    return points


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as fichier:
        writer = csv.DictWriter(fichier, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def plot_curve(
    points: Iterable[dict],
    x_key: str,
    y_key: str,
    title: str,
    x_label: str,
    y_label: str,
    path: Path,
    baseline: tuple[list[float], list[float]] | None = None,
) -> None:
    x = [row[x_key] for row in points]
    y = [row[y_key] for row in points]
    plt.figure(figsize=(6, 4))
    plt.plot(x, y, marker="o", markersize=3)
    if baseline is not None:
        plt.plot(baseline[0], baseline[1], linestyle="--", color="gray")
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path, dpi=160)
    plt.close()


def evaluate_policy(policy_dir: Path) -> dict | None:
    inspections_file = policy_dir / "inspections.csv"
    if not inspections_file.exists() or inspections_file.stat().st_size == 0:
        return None

    rows = lire_inspections(inspections_file)
    if not rows:
        return None

    default_tp = sum(1 for row in rows if int(row["vrai_defaut"]) == 1 and int(row["alerte"]) == 1)
    default_fp = sum(1 for row in rows if int(row["vrai_defaut"]) == 0 and int(row["alerte"]) == 1)
    default_tn = sum(1 for row in rows if int(row["vrai_defaut"]) == 0 and int(row["alerte"]) == 0)
    default_fn = sum(1 for row in rows if int(row["vrai_defaut"]) == 1 and int(row["alerte"]) == 0)

    p = precision(default_tp, default_fp)
    r = recall(default_tp, default_fn)
    spec = specificity(default_tn, default_fp)
    acc = accuracy(default_tp, default_fp, default_tn, default_fn)
    f1 = f1_score(p, r)
    bacc = balanced_accuracy(r, spec)

    roc_rows = build_roc_points(rows)
    pr_rows = build_pr_points(rows)
    roc_auc = auc_from_points([(row["fpr"], row["tpr"]) for row in roc_rows])
    pr_auc = auc_from_points([(row["recall"], row["precision"]) for row in pr_rows])

    output_dir = OUTPUT_ROOT / policy_dir.name
    write_csv(output_dir / "roc_curve.csv", roc_rows)
    write_csv(output_dir / "pr_curve.csv", pr_rows)

    plot_curve(
        roc_rows,
        x_key="fpr",
        y_key="tpr",
        title=f"ROC - {policy_dir.name}",
        x_label="False Positive Rate",
        y_label="True Positive Rate",
        path=output_dir / "roc_curve.png",
        baseline=([0.0, 1.0], [0.0, 1.0]),
    )
    plot_curve(
        pr_rows,
        x_key="recall",
        y_key="precision",
        title=f"Precision-Recall - {policy_dir.name}",
        x_label="Recall",
        y_label="Precision",
        path=output_dir / "pr_curve.png",
    )

    return {
        "politique": policy_dir.name,
        "n_inspections": len(rows),
        "tp": default_tp,
        "fp": default_fp,
        "tn": default_tn,
        "fn": default_fn,
        "accuracy": round(acc, 6),
        "precision": round(p, 6),
        "recall": round(r, 6),
        "specificity": round(spec, 6),
        "f1_score": round(f1, 6),
        "balanced_accuracy": round(bacc, 6),
        "roc_auc": round(roc_auc, 6),
        "pr_auc": round(pr_auc, 6),
    }


def main() -> None:
    summaries = []
    for child in ROOT.iterdir():
        if not child.is_dir() or child.name == "monte_carlo" or child.name == "ml_metrics":
            continue
        result = evaluate_policy(child)
        if result is not None:
            summaries.append(result)

    summaries.sort(key=lambda row: row["roc_auc"], reverse=True)
    write_csv(OUTPUT_ROOT / "classification_metrics.csv", summaries)

    print("=== Analyse ML / détection ===")
    if not summaries:
        print("Aucune politique avec inspections disponible.")
        return
    for row in summaries:
        print(
            f"- {row['politique']}: ROC AUC={row['roc_auc']}, PR AUC={row['pr_auc']}, "
            f"F1={row['f1_score']}, recall={row['recall']}, precision={row['precision']}"
        )


if __name__ == "__main__":
    main()
