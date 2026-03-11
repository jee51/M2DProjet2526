# Projet M2D - Simulateur de maintenance

## Objectif
Ce dépôt contient une base exploitable pour rendre rapidement le projet :
- simuler une flotte de systèmes avec usure progressive ;
- comparer plusieurs politiques de maintenance ;
- produire des jeux de données CSV ;
- estimer des indicateurs moyens et des intervalles de confiance par Monte Carlo.

## Fichiers principaux
- `simulateur_asija_gem.py` : simulateur principal et comparaison directe de politiques.
- `evaluation_monte_carlo.py` : réplications Monte Carlo et synthèse statistique.
- `data/` : sorties générées.
- `docs/` : documents du sujet.

## Hypothèses du modèle
Le modèle n'est pas un jumeau numérique industriel. C'est un modèle simple, cohérent avec le sujet académique.

### 1. Usage
Chaque système reçoit un niveau d'usage journalier aléatoire suivant une loi log-normale.

### 2. Usure
L'usure augmente chaque jour :
- proportionnellement à l'usage ;
- plus vite lorsque le composant vieillit ;
- avec une variabilité aléatoire.

Par défaut, l'incrément d'usure suit une loi log-normale. Une variante Weibull est aussi prévue dans le code si l'on souhaite tester une autre hypothèse de dégradation.

### 3. Détection
Une inspection observe un score bruité de l'usure :
- si le score dépasse un seuil, une alerte est levée ;
- l'alerte peut être vraie ou fausse selon le bruit.

### 4. Panne
La panne suit un risque journalier dépendant :
- de l'usure courante ;
- de l'âge du composant.

### 5. Maintenance
- `REPARATION` : réduit l'usure mais ne remet pas à neuf ;
- `REMPLACEMENT` : installe un composant neuf.

## Politiques comparées
- `corrective_pure` : on attend la panne.
- `conditionnelle_30j` : inspection tous les 30 jours, maintenance sur alerte.
- `systematique_200j` : remplacement systématique à 200 jours.
- `mixte_30j_plus_200j` : combinaison des deux précédentes.

## Exécution rapide
### Comparaison simple
```bash
python simulateur_asija_gem.py
```

### Monte Carlo
```bash
python evaluation_monte_carlo.py --repetitions 30 --n-systemes 200 --n-jours 730
```

## Sorties utiles
### Simulation simple
- `data/comparaison_politiques.csv`
- `data/<politique>/assets.csv`
- `data/<politique>/usage_log.csv`
- `data/<politique>/inspections.csv`
- `data/<politique>/maintenance.csv`
- `data/<politique>/pannes.csv`
- `data/<politique>/etat_journalier.csv`

### Monte Carlo
- `data/monte_carlo/replications.csv`
- `data/monte_carlo/synthese_monte_carlo.csv`

## Ce qu'il faut raconter dans le rendu
### 1. Partie modélisation
Présenter les hypothèses simples : usage, usure, inspection, panne, réparation, remplacement.

### 2. Partie résultats
Comparer les politiques sur :
- nombre de pannes ;
- coût total ;
- disponibilité.

### 3. Partie statistiques
Montrer qu'une seule simulation n'est pas suffisante.
Utiliser Monte Carlo pour donner :
- une moyenne ;
- un intervalle de confiance à 95%.

### 4. Limites à assumer franchement
- pas de calibration sur données réelles ;
- paramètres choisis de façon plausible mais non identifiés ;
- un seul mode de défaillance ;
- pas de stock de pièces ni de ressource équipe.

## Recommandation pour la soutenance
Si vous manquez de temps, assumez une posture honnête :
- "Nous avons construit un simulateur simple mais cohérent" ;
- "Nous avons préféré un modèle lisible et justifiable à un modèle artificiellement complexe" ;
- "La prochaine étape serait le calibrage/inversion sur données observées".
