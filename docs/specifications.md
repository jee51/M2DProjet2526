Spécifications Techniques - Simulateur de Maintenance



Projet M2D 2025-2026

Équipe : ASIJA (Alan, Sadibou, Ibrahima, Jalil, Athis)



1\. Contexte et Objectifs



L'objectif est de développer un simulateur d'endommagement pour une flotte de composants industriels. Ce simulateur permettra d'évaluer différentes politiques de maintenance en modélisant :



Le vieillissement naturel des composants.



L'impact des inspections (détection imparfaite).



Les coûts associés (réparation préventive vs panne).



2\. Architecture Technique



Le projet est structuré selon une architecture modulaire en Python.



2.1 Stack Technologique



Langage : Python 3.10+



Bibliothèques Core : numpy (calcul matriciel), pandas (gestion des logs), scipy (lois de probabilité).



Interface Utilisateur : Streamlit (pour les tableaux de bord interactifs et la simulation en temps réel).



Qualité de code : pytest pour les tests unitaires.



2.2 Structure du Code (src/)



simulation.py (Moteur) : Contient la classe System et Fleet. Gère l'évolution du temps t -> t+1.



maintenance.py (Logique) : Contient les stratégies d'inspection (périodique, conditionnelle) et la simulation du détecteur.



utils.py : Fonctions de génération de lois aléatoires (Weibull, Gamma).



3\. Modélisation Mathématique (Proposition)



3.1 Loi de dégradation



Nous proposons d'utiliser un processus Gamma (ou une loi de Weibull pour la durée de vie) pour modéliser l'endommagement progressif.

Soit $X(t)$ le niveau de dégradation au temps $t$.

L'incrément de dégradation suit une loi Gamma :



$$\\Delta X \\sim \\Gamma(\\alpha \\cdot \\Delta t, \\beta)$$



3.2 Modèle de Détection



Le détecteur est imparfait. La probabilité de détecter une panne dépend du niveau d'usure $x$ :



$$P(\\text{Détection} | \\text{Usure} = x) = \\frac{1}{1 + e^{-(ax+b)}}$$



(Fonction sigmoïde à calibrer).



4\. Architecture des Données



Les données seront stockées sous forme de fichiers Parquet ou CSV dans le dossier data/.



Schéma de la table logs\_maintenance :

| Timestamp | System\_ID | Event\_Type | Cost | Usure\_Reelle | Usure\_Mesuree |

|-----------|-----------|------------|------|--------------|---------------|

| 10:00     | S\_01      | Inspection | 50   | 12.5         | 12.0          |

| 10:05     | S\_42      | Panne      | 500  | 100.0        | N/A           |



5\. Plan de Travail (Lots)



Lot 1 : Architecture \& Spécifications (Semaine 1)



Lot 2 : Moteur de vieillissement (Semaine 2)



Lot 3 : Module de maintenance et détection (Semaine 3)



Lot 4 : Interface graphique et visualisation (Semaine 4)



Lot 5 : Analyse des coûts et optimisation (Semaine 5)



Lot 6 : Inversion du modèle (Bonus)

