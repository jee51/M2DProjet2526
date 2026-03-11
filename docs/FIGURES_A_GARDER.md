# Figures et tableaux à garder

## 1. Tableau principal de comparaison
Source : [data/comparaison_politiques.csv](../data/comparaison_politiques.csv#L1-L5)

À garder dans le rapport sous forme de tableau synthétique.
Colonnes recommandées :
- politique
- nombre de pannes
- nombre de maintenances
- coût total
- disponibilité

Commentaire conseillé :
> La politique corrective pure est nettement dominée en coût. Les politiques préventives réduisent fortement le nombre de pannes. Dans notre paramétrage actuel, les politiques conditionnelle et systématique offrent le meilleur compromis coût/risque.

## 2. Tableau Monte Carlo
Source : [data/monte_carlo/synthese_monte_carlo.csv](../data/monte_carlo/synthese_monte_carlo.csv#L1-L5)

À garder pour montrer que les conclusions ne reposent pas sur un seul tirage.
Colonnes recommandées :
- politique
- coût moyen
- intervalle de confiance à 95% sur le coût
- nombre moyen de pannes
- disponibilité moyenne

Commentaire conseillé :
> L'analyse Monte Carlo confirme la hiérarchie générale observée sur une simulation simple et donne une mesure explicite de l'incertitude associée aux résultats.

## 3. Courbe ROC
Source recommandée : [data/ml_metrics/conditionnelle_30j/roc_curve.png](../data/ml_metrics/conditionnelle_30j/roc_curve.png)

Pourquoi la garder :
- figure visuelle simple
- montre la qualité de séparation du détecteur
- facile à commenter à l'oral

Commentaire conseillé :
> Une aire sous la courbe ROC élevée indique que le score d'inspection sépare correctement les états sains et dégradés sur l'ensemble des seuils possibles.

## 4. Courbe Precision-Recall
Source recommandée : [data/ml_metrics/conditionnelle_30j/pr_curve.png](../data/ml_metrics/conditionnelle_30j/pr_curve.png)

Pourquoi la garder :
- utile lorsque les défauts ne sont pas majoritaires
- complète bien la courbe ROC

Commentaire conseillé :
> La courbe Precision-Recall permet d'évaluer le compromis entre détection des défauts et maîtrise des fausses alertes, ce qui est particulièrement pertinent pour une politique de maintenance conditionnelle.

## 5. Tableau des métriques de classification
Source : [data/ml_metrics/classification_metrics.csv](../data/ml_metrics/classification_metrics.csv#L1-L3)

Colonnes recommandées :
- politique
- précision
- rappel
- score F1
- ROC AUC
- PR AUC

Commentaire conseillé :
> Les métriques de classification montrent que le détecteur simulé est globalement performant, tout en conservant des erreurs de détection réalistes.

## 6. Ce qu'il faut éviter
À éviter dans le rapport final si le temps manque :
- toutes les tables détaillées `usage_log.csv`
- tout le contenu de `etat_journalier.csv`
- les détails complets des réplications Monte Carlo

Ces fichiers sont utiles pour la traçabilité, mais pas indispensables dans le document principal.
