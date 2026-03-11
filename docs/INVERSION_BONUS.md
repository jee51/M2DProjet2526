# Bonus : inversion du problème

## Idée générale
Le simulateur principal résout le **problème direct** :

- on fixe des paramètres ;
- on simule l'usage, l'usure, les inspections, les maintenances et les pannes.

L'**inversion du problème** consiste à faire l'inverse :

- on part de données observées ;
- on cherche les paramètres du modèle capables de reproduire au mieux ces données.

## Ce que fait le script
Le fichier [inversion_modele.py](../inversion_modele.py) propose une approche simple de calibration.

### Étape 1 : estimation directe de la loi d'usage
À partir de `usage_log.csv`, le script estime :
- `usage_log_mu`
- `usage_log_sigma`

Ces deux paramètres sont obtenus directement à partir des usages observés, en travaillant sur le logarithme des quantités.

### Étape 2 : calibration par simulation
Ensuite, le script cherche par essais successifs des valeurs plausibles pour :
- `usure_base`
- `usure_age_facteur`
- `lambda_panne_base`
- `lambda_panne_usure`
- `lambda_panne_age`
- `inspection_noise_std`
- `fraction_usure_restante_apres_reparation`

Pour chaque candidat :
1. on relance le simulateur avec ces paramètres ;
2. on calcule des indicateurs simulés ;
3. on compare ces indicateurs aux données observées.

Le meilleur candidat est celui qui minimise une distance globale entre :
- nombre de pannes,
- nombre de maintenances,
- nombre d'inspections,
- coût total,
- coût de panne,
- disponibilité,
- usure moyenne,
- proportion de systèmes dégradés,
- statistiques sur les inspections.

## Nature de la méthode
Cette approche n'est pas une estimation statistique optimale au sens théorique. C'est une méthode de calibration **simulation-based** ou **par recherche sur l'espace des paramètres**.

Elle est néanmoins très pertinente pour un bonus de projet, car elle montre que :
- le problème inverse a bien été compris ;
- le simulateur direct peut servir de base à une calibration ;
- on peut déjà proposer une première méthode pratique d'estimation.

