# Rapport - version de travail

## 1. Introduction et problématique
Dans le cadre du projet M2D, nous nous intéressons à la modélisation simplifiée de la maintenance d'une flotte de systèmes comportant chacun un composant susceptible de se dégrader progressivement puis de tomber en panne. L'objectif principal est de construire un simulateur probabiliste permettant de générer des données cohérentes, de comparer plusieurs politiques de maintenance et d'évaluer leur impact sur le nombre de pannes, la disponibilité des systèmes et le coût global.

Le projet vise également à produire une base de travail exploitable pour des analyses ultérieures, en particulier l'inversion du modèle et le calibrage de paramètres à partir de données observées. Dans cette optique, le simulateur doit rester suffisamment simple pour être lisible, mais assez riche pour capturer les mécanismes essentiels du problème : usage variable, usure cumulative, inspections imparfaites, maintenance corrective, maintenance préventive et coûts associés.

## 2. Hypothèses de modélisation
Pour rester cohérent avec le sujet et livrer un modèle exploitable dans le temps imparti, plusieurs hypothèses simplificatrices ont été retenues.

- Tous les systèmes sont supposés identiques.
- Chaque système ne possède qu'un seul composant critique.
- Le composant se dégrade de manière progressive sous l'effet de l'usage et du vieillissement.
- Une panne devient plus probable lorsque l'usure et l'âge augmentent.
- Lors d'une inspection, on n'observe pas directement l'usure réelle, mais un score bruité.
- Une réparation réduit l'usure sans remettre le composant totalement à neuf.
- Un remplacement remet le composant à l'état neuf.

Ces hypothèses permettent de construire un modèle stochastique clair et défendable. Le but n'est pas de reproduire exactement un système industriel réel, mais de disposer d'un simulateur paramétrable pour comparer des politiques de maintenance.

## 3. Lois probabilistes retenues
### 3.1 Usage journalier
L'usage journalier est modélisé par une loi log-normale. Ce choix est naturel car l'usage est strictement positif, asymétrique, et certaines journées peuvent être plus chargées que la moyenne.

### 3.2 Incrément d'usure
L'incrément d'usure journalier suit par défaut une loi log-normale, avec une moyenne dépendant de l'usage du jour et de l'âge du composant. Une variante Weibull est également implémentée dans le code afin de tester une hypothèse alternative de dégradation. Ce choix répond au besoin d'éviter un modèle trop déterministe.

### 3.3 Inspection
Lors d'une inspection, le détecteur produit un score égal à l'usure réelle perturbée par un bruit gaussien centré. Une alerte est levée lorsque ce score dépasse un seuil. Ce mécanisme permet de représenter simplement les vrais positifs, faux positifs et faux négatifs.

### 3.4 Panne
La panne n'est pas tirée à date fixe. Le modèle utilise un risque journalier croissant avec l'usure et l'âge. Cette approche est plus réaliste qu'un temps de panne figé, car elle permet à la probabilité de défaillance d'évoluer au fil du temps.

## 4. Architecture des données simulées
Le simulateur produit plusieurs tables CSV, organisées par politique de maintenance.

- `assets.csv` : composants installés au cours du temps
- `usage_log.csv` : usage journalier et incrément d'usure
- `inspections.csv` : résultats des inspections
- `maintenance.csv` : réparations et remplacements
- `pannes.csv` : événements de panne
- `etat_journalier.csv` : état quotidien de chaque système
- `resume.csv` : synthèse locale pour une politique

Un tableau global de comparaison est aussi produit dans [data/comparaison_politiques.csv](../data/comparaison_politiques.csv#L1-L5).

## 5. Politiques de maintenance comparées
Quatre politiques ont été comparées.

### 5.1 Politique corrective
La politique `corrective_pure` consiste à ne réaliser aucune inspection ni action préventive. Le composant est remplacé uniquement lorsqu'une panne survient.

### 5.2 Politique conditionnelle
La politique `conditionnelle_30j` repose sur une inspection tous les 30 jours. Lorsque le score d'inspection dépasse un seuil, une maintenance est déclenchée.

### 5.3 Politique systématique
La politique `systematique_200j` consiste à remplacer automatiquement le composant lorsque son âge atteint 200 jours, indépendamment de son état observé.

### 5.4 Politique mixte
La politique `mixte_30j_plus_200j` combine une inspection tous les 30 jours et un remplacement systématique à 200 jours.

## 6. Résultats principaux
Les premiers résultats sont synthétisés dans [data/comparaison_politiques.csv](../data/comparaison_politiques.csv#L1-L5).

On observe que :
- la politique corrective pure est la plus coûteuse en raison du nombre élevé de pannes ;
- les politiques préventives réduisent fortement le nombre de pannes ;
- la politique systématique et la politique conditionnelle ont des coûts globaux proches ;
- la politique mixte réduit davantage les pannes mais au prix d'une sur-maintenance et d'un coût plus élevé.

Ces résultats montrent qu'une stratégie purement corrective n'est pas souhaitable dans le cadre du modèle simulé. Ils montrent également qu'une politique plus agressive n'est pas automatiquement la meilleure en coût global.

## 7. Analyse statistique par Monte Carlo
Une unique simulation ne suffit pas pour conclure, car les résultats dépendent des tirages aléatoires. Pour cette raison, une analyse Monte Carlo a été menée avec plusieurs réplications par politique. La synthèse est disponible dans [data/monte_carlo/synthese_monte_carlo.csv](../data/monte_carlo/synthese_monte_carlo.csv#L1-L5).

Cette analyse permet de calculer, pour chaque politique :
- un coût total moyen ;
- un nombre moyen de pannes ;
- une disponibilité moyenne ;
- un intervalle de confiance à 95% sur ces indicateurs.

L'intérêt de cette étape est double : elle renforce la robustesse de la comparaison et elle rend l'analyse plus crédible dans un contexte probabiliste.

## 8. Analyse du détecteur comme système de classification
Les inspections simulées ont été exploitées comme un problème de classification binaire : défaut réel contre absence de défaut. Une analyse inspirée du machine learning a été réalisée, avec calcul de métriques telles que la précision, le rappel, le score F1, l'aire sous la courbe ROC et l'aire sous la courbe Precision-Recall. Les résultats sont regroupés dans [data/ml_metrics/classification_metrics.csv](../data/ml_metrics/classification_metrics.csv#L1-L3).

Cette partie permet d'évaluer la qualité du détecteur indépendamment des seuls coûts de maintenance. Elle donne une lecture complémentaire : une politique peut être bonne économiquement sans que le détecteur soit parfait, et inversement.

## 9. Conclusion
Le projet a permis de construire un simulateur probabiliste simple, cohérent et paramétrable pour l'étude de politiques de maintenance. Malgré son caractère volontairement simplifié, le modèle permet déjà de comparer plusieurs stratégies, de produire des indicateurs économiques et opérationnels, et de quantifier l'incertitude des résultats par Monte Carlo.

La suite naturelle de ce travail serait le calibrage du modèle à partir de données réelles, l'ajout de contraintes supplémentaires comme les ressources de maintenance ou les stocks de pièces, et l'étude d'autres politiques de décision.
