# Support de lecture du code

Ce document sert de support de relecture rapide pendant la présentation. Il explique :
- comment les paramètres du simulateur ont été choisis ;
- le rôle des principales fonctions ;
- l'interprétation de certains comportements observés dans les résultats.

## 1. Philosophie générale du modèle
Le simulateur n'est pas calibré sur des données industrielles réelles. Il s'agit d'un modèle probabiliste simple conçu pour être :
- lisible ;
- défendable académiquement ;
- suffisamment stochastique ;
- capable de discriminer plusieurs politiques de maintenance.

L'idée est donc de fixer des paramètres plausibles plutôt que d'affirmer une fidélité industrielle parfaite.

## 2. Choix des paramètres globaux
Les paramètres sont définis dans [simulateur_asija_gem.py](../simulateur_asija_gem.py#L13-L46).

### 2.1 Taille de simulation
- `n_systemes = 200` : permet d'avoir une flotte suffisamment grande pour lisser un peu les aléas.
- `n_jours = 730` : deux ans de simulation, ce qui laisse apparaître plusieurs événements de maintenance et de panne.

### 2.2 Usage
- `usage_log_mu = 1.0`
- `usage_log_sigma = 0.45`

Ces paramètres donnent un usage journalier positif, variable, avec quelques journées plus intenses. Le choix d'une loi log-normale évite un usage négatif et introduit une asymétrie réaliste.

### 2.3 Usure
- `usure_base = 0.0025`
- `usure_age_facteur = 0.35`
- `loi_usure = "lognormal"`
- `usure_log_sigma = 0.55`
- `usure_weibull_shape = 1.8`

L'idée est la suivante :
- l'usure augmente avec l'usage ;
- elle devient plus rapide quand le composant vieillit ;
- elle reste aléatoire d'un jour à l'autre.

Le choix par défaut d'une loi log-normale permet d'éviter un modèle trop déterministe. Une variante Weibull est disponible pour tester une autre hypothèse de dégradation.

### 2.4 Détection
- `inspection_noise_std = 0.20`
- `seuil_defaut = 1.00`
- `seuil_remplacement = 1.50`

Le score d'inspection est bruité. Le seuil de défaut représente le niveau à partir duquel le composant est considéré comme dégradé. Le seuil de remplacement est plus élevé : en dessous, on répare ; au-dessus, on remplace.

### 2.5 Panne
- `lambda_panne_base = 0.00015`
- `lambda_panne_usure = 1.10`
- `lambda_panne_age = 0.20`

Ces paramètres ont été choisis pour obtenir :
- peu de pannes au début de vie ;
- une augmentation du risque avec l'usure ;
- une influence de l'âge même à usure comparable.

### 2.6 Coûts
- inspection : `60`
- réparation : `500`
- remplacement : `1800`
- panne : `4000 + part usure + part arrêt`

Le principe économique retenu est simple : la panne doit coûter nettement plus cher que la prévention. Cela permet d'évaluer si une politique plus proactive peut réduire le coût total malgré des actions de maintenance plus fréquentes.

## 3. Lecture des fonctions principales

## 3.1 Structures de données
### `ConfigSimulation`
Contient tous les paramètres du modèle.

### `PolitiqueMaintenance`
Définit la logique de décision : inspection oui/non, fréquence, seuil, remplacement systématique.

### `EtatActif`
Représente l'état courant d'un composant sur un système : âge, usure, date du prochain contrôle, indisponibilité.

## 3.2 Fonctions de base
### `generer_id()`
Crée un identifiant unique pour les actifs, inspections, pannes ou maintenances.

### `_tirer_delai_inspection()`
Tire le prochain délai d'inspection autour d'une moyenne. Cela permet d'éviter des inspections parfaitement périodiques.

### `_tirer_usage()`
Tire l'usage journalier suivant une loi log-normale.

### `_increment_usure()`
Calcule l'incrément d'usure du jour. La moyenne dépend :
- de l'usage du jour ;
- de l'âge du composant.

Ensuite, la variabilité est introduite via la loi choisie (log-normale, Weibull ou Gamma).

### `_probabilite_panne_journaliere()`
Calcule la probabilité de panne du jour à partir de l'usure et de l'âge.

Le mécanisme est :
1. calcul d'une intensité de panne ;
2. transformation de cette intensité en probabilité journalière.

## 3.3 Gestion des événements
### `_effectuer_inspection()`
Cette fonction :
1. calcule un score bruité ;
2. décide s'il y a alerte ;
3. enregistre l'inspection ;
4. déclenche éventuellement une réparation ou un remplacement.

### `_appliquer_maintenance()`
Cette fonction applique la maintenance :
- enregistrement dans la table `maintenance` ;
- réduction partielle de l'usure en cas de réparation ;
- remise à neuf complète en cas de remplacement ;
- mise à jour du temps d'indisponibilité.

## 3.4 Boucle principale
### `executer()`
C'est la fonction la plus importante. Pour chaque jour et pour chaque système, elle exécute l'ordre logique suivant :
1. vérifier si le système est indisponible ;
2. vérifier si une maintenance systématique doit être faite ;
3. vérifier si une inspection doit être faite ;
4. tirer l'usage du jour ;
5. calculer l'usure du jour ;
6. calculer la probabilité de panne ;
7. tirer la panne ou non ;
8. enregistrer l'état du jour.

## 4. Explication détaillée du test de panne
La portion suivante apparaît dans [simulateur_asija_gem.py](../simulateur_asija_gem.py#L342-L358) :

```python
proba_panne = self._probabilite_panne_journaliere(etat.usure, age_jours)
if self.rng.random() < proba_panne:
    duree_arret = self.config.duree_remplacement_jours
    cout_panne = self._cout_panne(etat.usure, duree_arret)
```

### Signification
- `proba_panne` est une probabilité comprise entre `0` et `1`.
- `self.rng.random()` tire un nombre aléatoire uniforme entre `0` et `1`.
- si ce tirage est plus petit que `proba_panne`, alors la panne a lieu.

### Interprétation probabiliste
Si `proba_panne = 0.03`, cela veut dire que le système a `3 %` de chance de tomber en panne ce jour-là.

On tire ensuite un nombre aléatoire :
- si le tirage vaut `0.01`, alors `0.01 < 0.03`, donc panne ;
- si le tirage vaut `0.40`, alors `0.40 > 0.03`, donc pas de panne.

C'est une simulation classique d'un événement aléatoire de Bernoulli.

## 4.b Pourquoi certaines quantités sont bornées avec `max(...)` ?
Dans plusieurs fonctions du code, certaines quantités sont forcées à rester au-dessus d'une très petite borne positive, par exemple :

```python
moyenne = max(1e-8, moyenne)
sigma = max(1e-6, self.config.usure_log_sigma)
shape = max(1e-6, self.config.usure_weibull_shape)
```

L'objectif n'est pas de modifier le sens physique du modèle, mais d'éviter des problèmes numériques.

### Pourquoi est-ce utile ?
- une loi log-normale ne peut pas utiliser une moyenne nulle ou négative ;
- une loi Weibull ou Gamma exige des paramètres strictement positifs ;
- une exponentielle avec un exposant trop grand peut devenir numériquement instable.

### Exemple
Dans le calcul de l'usure, on utilise parfois un logarithme ou des paramètres de forme de loi probabiliste. Si une quantité vaut exactement `0` ou devient négative, le calcul peut devenir invalide. On ajoute donc une petite borne positive pour garder un modèle robuste.

### Interprétation correcte
Il faut voir ces `max(...)` comme des garde-fous numériques. Ils permettent au simulateur de rester stable même si un paramètre est très petit ou si l'état du système se trouve dans une zone extrême.

## 5. Pourquoi la politique corrective pure coûte plus cher ?
La politique `corrective_pure` n'effectue ni inspection ni prévention. Elle n'agit qu'après panne.

Cela semble moins coûteux à première vue, car on évite les inspections et une partie des maintenances. Pourtant, dans le modèle, la panne est volontairement chère :
- coût fixe élevé ;
- coût lié à l'usure ;
- coût lié à l'arrêt.

Donc la logique est la suivante :
- moins de prévention ;
- plus de pannes ;
- pannes beaucoup plus coûteuses ;
- coût total final plus élevé.

Autrement dit, économiser la prévention ne signifie pas minimiser le coût global.

## 6. Ce qu'il faut dire à l'oral
Voici une version courte et propre :

> Les paramètres du simulateur n'ont pas été calibrés sur des données réelles ; ils ont été choisis pour être plausibles et pour produire des différences lisibles entre politiques. Le cœur du simulateur est la boucle journalière : on tire un usage, on met à jour l'usure, on calcule un risque de panne, puis on décide aléatoirement si la panne survient. La politique corrective pure coûte davantage parce qu'elle laisse se produire beaucoup plus de pannes, or une panne coûte beaucoup plus cher qu'une inspection ou une réparation préventive.

## 7. Ce qu'il faut assumer si on te challenge
- le modèle est simple mais volontairement probabiliste ;
- les paramètres sont de travail, pas des paramètres identifiés ;
- l'objectif principal est la comparaison de politiques, pas la prédiction industrielle exacte ;
- la suite logique serait un calibrage sur données observées.

## 8. Bonus : inversion du problème
Le sujet mentionne aussi un problème inverse. L'idée est la suivante :

- dans le problème direct, on fixe des paramètres puis on simule les données ;
- dans le problème inverse, on part de données observées et on essaie de retrouver les paramètres qui pourraient les expliquer.

Dans le projet, cette idée a été abordée dans [inversion_modele.py](../inversion_modele.py).

### Ce que fait ce script
1. Il lit un dossier de données observées, par exemple `data/conditionnelle_30j`.
2. Il estime directement les paramètres de la loi d'usage à partir de `usage_log.csv`.
3. Il génère plusieurs jeux de paramètres candidats pour l'usure, la panne et la qualité du détecteur.
4. Pour chaque candidat, il relance le simulateur.
5. Il compare les statistiques simulées aux statistiques observées.
6. Il conserve le candidat qui minimise l'écart global.

### Que contient `observed_vs_simulated_best.csv` ?
Le fichier [data/inversion_conditionnelle/observed_vs_simulated_best.csv](../data/inversion_conditionnelle/observed_vs_simulated_best.csv) compare :
- les statistiques \textbf{observées},
- les statistiques \textbf{simulées} avec le meilleur jeu de paramètres trouvé.

Dans le cas actuel, ces données proviennent de la politique `conditionnelle_30j`, car l'inversion a été lancée avec le dossier observé `data/conditionnelle_30j`.

### Comment lire les colonnes
- `observed` : valeur mesurée dans les données observées ;
- `simulated_best` : valeur simulée avec le meilleur candidat ;
- `abs_error` : écart absolu entre les deux ;
- `relative_error` : écart relatif, c'est-à-dire l'erreur rapportée à la valeur observée.

### Comment en parler à l'oral
Tu peux dire :

> En bonus, nous avons utilisé les données simulées comme si elles étaient observées, puis nous avons cherché des paramètres capables de reproduire au mieux leurs statistiques globales. Cela ne constitue pas une identification rigoureuse au sens théorique, mais c'est une première approche de calibration du simulateur, cohérente avec l'idée d'inversion du problème mentionnée dans le sujet.
