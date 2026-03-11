# Compilation Overleaf

## Fichier principal
Utiliser : [docs/slides_overleaf.tex](slides_overleaf.tex)

## Pour compiler sur Overleaf
Le plus simple est d'uploader l'ensemble du dossier projet, ou au minimum :
- `docs/slides_overleaf.tex`
- `data/presentation_figures/couts_politiques.png`
- `data/presentation_figures/pannes_disponibilite.png`
- `data/presentation_figures/monte_carlo_couts.png`
- `data/ml_metrics/conditionnelle_30j/roc_curve.png`

En conservant l'arborescence, les chemins relatifs fonctionneront directement.

## Si tu veux aller vite
Tu peux aussi déplacer temporairement les images dans le même dossier que le `.tex` sur Overleaf puis adapter les chemins `\includegraphics`.

## Slides incluses
Le fichier contient déjà :
- page de titre
- problématique
- hypothèses et lois
- politiques comparées
- résultats coûts
- résultats pannes / disponibilité
- Monte Carlo
- métriques de détection type ML
- conclusion
