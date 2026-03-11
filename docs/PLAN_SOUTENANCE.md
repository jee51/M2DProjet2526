# Plan de soutenance

## Slide 1 - Sujet et objectif
Titre suggéré :
**Simulation probabiliste de politiques de maintenance pour une flotte de systèmes**

À dire :
- le problème porte sur une flotte de systèmes avec dégradation progressive ;
- l'objectif est de comparer plusieurs politiques de maintenance ;
- le livrable est un simulateur paramétrable et des indicateurs de performance.

## Slide 2 - Hypothèses du modèle
À mettre :
- usage aléatoire
- usure progressive
- inspections imparfaites
- panne plus probable avec l'usure et l'âge
- réparation partielle, remplacement à neuf

À dire :
- le modèle est volontairement simple ;
- il ne prétend pas être un jumeau industriel ;
- il est conçu pour comparer des politiques de décision.

## Slide 3 - Lois probabilistes et architecture
À mettre :
- usage : log-normal
- usure : log-normal ou Weibull
- inspection : score bruité
- panne : risque journalier croissant

À dire :
- le modèle évite un comportement trop déterministe ;
- l'incertitude est intégrée à toutes les étapes clés.

## Slide 4 - Politiques comparées
Tableau simple avec 4 lignes :
- corrective
- conditionnelle 30 jours
- systématique 200 jours
- mixte

À dire :
- ces politiques couvrent les grandes familles de maintenance demandées dans le sujet.

## Slide 5 - Résultats principaux
Source : [data/comparaison_politiques.csv](../data/comparaison_politiques.csv#L1-L5)

À mettre :
- nombre de pannes
- coût total
- disponibilité

À dire :
- la corrective pure est clairement la moins bonne ;
- la systématique et la conditionnelle donnent les meilleurs compromis ;
- la mixte réduit les pannes mais coûte davantage.

## Slide 6 - Robustesse statistique
Source : [data/monte_carlo/synthese_monte_carlo.csv](../data/monte_carlo/synthese_monte_carlo.csv#L1-L5)

À mettre :
- coût moyen
- intervalle de confiance 95%

À dire :
- on ne conclut pas sur une seule simulation ;
- Monte Carlo permet de quantifier la variabilité.

## Slide 7 - Qualité du détecteur
Sources :
- [data/ml_metrics/classification_metrics.csv](../data/ml_metrics/classification_metrics.csv#L1-L3)
- [data/ml_metrics/conditionnelle_30j/roc_curve.png](../data/ml_metrics/conditionnelle_30j/roc_curve.png)

À dire :
- les inspections peuvent être vues comme un problème de classification ;
- on évalue donc la qualité du détecteur par des métriques de type machine learning.

## Slide 8 - Limites et perspectives
À dire :
- paramètres non calibrés sur données réelles ;
- un seul composant critique par système ;
- pas de contrainte de stock ou d'équipe de maintenance.

Conclusion proposée :
> Le projet aboutit à un simulateur stochastique cohérent, utile pour comparer des politiques de maintenance et préparer un travail ultérieur de calibration sur données réelles.
