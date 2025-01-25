# Système d'Automatisation d'Achats Asynchrones

## 🚀 Description du Projet

Un système sophistiqué d'automatisation d'achats en ligne utilisant Python, FastAPI et des techniques de requêtes asynchrones. Conçu pour effectuer des achats programmés avec haute performance et fiabilité.

## 📋 Fonctionnalités Principales

- Authentification web sécurisée
- Achats groupés programmés
- Gestion asynchrone des requêtes
- Suivi en temps réel des statuts d'achats
- Gestion avancée des erreurs et performances

## 🔧 Technologies Utilisées

- FastAPI
- aiohttp
- asyncio
- BeautifulSoup
- Python 3.9+

## 🛠 Installation

### Prérequis

- Python 3.9 ou supérieur
- Debian/Linux
- Accès Internet

### Étapes d'Installation

1. Cloner le dépôt
2. Créer un environnement virtuel
3. Installer les dépendances

```bash
git clone [URL_DU_DEPOT]
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 🚀 Démarrage

```bash
uvicorn main:app --reload
```

## 📡 Endpoints API

- `POST /schedule-purchases`: Planifier des achats
- `GET /purchase-status/{request_id}`: Vérifier le statut

## 🔒 Configuration

Modifier les constantes dans `main.py`:
- `BASE_URL`
- `LOGIN`
- `PASSWORD`

## 📊 Métriques et Logging

Suivi détaillé des performances:
- Temps de connexion
- Durée des requêtes
- Statut des achats

## ⚠️ Avertissements

- Utilisation à vos risques et périls
- Respecter les conditions d'utilisation du site cible

## 📝 Licence

Copyright (c) [2025] [Jean-Pierre Dupuis]

Ce projet est fourni "tel quel", sans garantie d'aucune sorte, expresse ou implicite. En aucun cas les auteurs ne pourront être tenus responsables de tout dommage, réclamation ou autre responsabilité découlant de, hors de ou en relation avec le logiciel ou son utilisation.

L'utilisation de ce logiciel est à vos propres risques. Il est de la responsabilité de l'utilisateur de s'assurer que l'utilisation de ce logiciel est conforme aux conditions d'utilisation des sites web ciblés et à toutes les lois et réglementations applicables.

La redistribution et l'utilisation sous forme de code source et binaire, avec ou sans modification, sont autorisées à condition que les conditions suivantes soient remplies:

1. Les redistributions du code source doivent conserver l'avis de droit d'auteur ci-dessus, cette liste de conditions et la clause de non-responsabilité suivante.
2. Les redistributions sous forme binaire doivent reproduire l'avis de droit d'auteur ci-dessus, cette liste de conditions et la clause de non-responsabilité suivante dans la documentation et/ou d'autres matériaux fournis avec la distribution.
3. Ni le nom du titulaire du droit d'auteur ni les noms de ses contributeurs ne peuvent être utilisés pour approuver ou promouvoir des produits dérivés de ce logiciel sans autorisation écrite préalable spécifique.
