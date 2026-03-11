# Plan de rendu sur 2 jours

## Jour 1 - sécuriser le fond

### 1. Expliquer le modèle
Dans le rapport, décrire très simplement :
- la flotte de systèmes ;
- l'usage aléatoire ;
- l'usure cumulative ;
- les inspections périodiques ;
- la panne par risque journalier ;
- la réparation et le remplacement.

### 2. Montrer les politiques comparées
Utiliser le tableau issu de `data/comparaison_politiques.csv`.

### 3. Ajouter la partie statistique
Utiliser `data/monte_carlo/synthese_monte_carlo.csv` pour justifier :
- moyenne du coût ;
- moyenne du nombre de pannes ;
- intervalle de confiance 95%.

## Jour 2 - sécuriser la forme

### 1. Rapport écrit
Structure recommandée :
1. Problème et objectifs
2. Hypothèses de modélisation
3. Architecture des données
4. Description des politiques de maintenance
5. Résultats de simulation
6. Analyse Monte Carlo
7. Limites et perspectives

### 2. Soutenance
Préparer 6 à 8 slides maximum :
1. Sujet
2. Hypothèses
3. Schéma logique du simulateur
4. Données générées
5. Comparaison des politiques
6. Monte Carlo
7. Limites
8. Conclusion

### 3. Message final à tenir
Le bon message n'est pas :
- "notre modèle est parfaitement réaliste"

Le bon message est :
- "notre modèle est simple, cohérent, paramétrable et exploitable pour comparer des politiques".

## Si vous manquez vraiment de temps
Priorité absolue :
1. rendre le simulateur propre ;
2. montrer un comparatif de politiques ;
3. montrer un intervalle de confiance ;
4. assumer les limites.
