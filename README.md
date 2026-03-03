# Scanner OSINT

Scanner de renseignement OSINT (Open Source Intelligence) pour les marchés prédictifs Polymarket. Collecte, analyse et priorise des signaux provenant de 13 sources de données pour détecter des opportunités de trading **avant** la couverture médiatique.

## Architecture

```
scanner-osint/
├── backend/          # FastAPI + SQLite + 13 collecteurs
├── frontend/         # Next.js 15 + TypeScript + Tailwind CSS
├── start.sh          # Lancer backend + frontend
└── stop.sh           # Arrêter les services
```

**Backend** : FastAPI, SQLAlchemy 2.0 (async), aiosqlite, httpx, VADER Sentiment
**Frontend** : Next.js 15, TypeScript, Tailwind CSS 4, Axios
**Base de données** : SQLite (zéro configuration)

## 13 Sources de données

### Actualités / Données (5)
| Source | Description | Clé API |
|--------|------------|---------|
| **GDELT** | Événements mondiaux en temps réel | Non |
| **NewsData.io** | Articles d'actualité | Oui (gratuit) |
| **ACLED** | Données de conflits armés | Oui (gratuit) |
| **Finnhub** | Actualités marchés financiers | Oui (gratuit) |
| **Reddit** | Subreddits géopolitique et prédictions | Non |

### FININT - Renseignement Financier (3)
| Source | Description | Clé API |
|--------|------------|---------|
| **SEC EDGAR** | Déclarations 8-K, Form 4 (délits d'initiés) | Non |
| **Whale Crypto** | Grosses transactions ETH (Etherscan) | Oui (gratuit) |
| **FRED** | Données Fed : PIB, IPC, chômage, taux | Oui (gratuit) |

### GEOINT - Renseignement Géospatial (3)
| Source | Description | Clé API |
|--------|------------|---------|
| **OpenSky ADS-B** | Suivi d'avions militaires/gouvernementaux | Non |
| **NASA FIRMS** | Détection satellite d'incendies en zones de conflit | Non |
| **Ship Tracker** | Activité maritime dans les détroits stratégiques | Non |

### OSINT Social (2)
| Source | Description | Clé API |
|--------|------------|---------|
| **Telegram** | Canaux OSINT publics (intel_slava, CIG, Rybar) | Non |
| **RSS Gouvernements** | Maison Blanche, DoD, UE, OTAN, ONU | Non |

## Pipeline de traitement

```
Collecte → Déduplication (SHA-256) → Sentiment VADER → Scoring (0-100) → Matching Polymarket → Résumés
```

**Formule de scoring** :
`relevance×30 + |sentiment|×20 + récence×20 + crédibilité_source×15 + match_marché×15 + bonus_OSINT(+10)`

Les sources de données brutes (SEC, FRED, ADS-B, NASA, etc.) reçoivent un bonus de +10 points car elles fournissent de l'information avant les médias.

## Installation

### Prérequis
- Python 3.10+
- Node.js 18+

### Backend
```bash
cd backend
python3 -m pip install -r requirements.txt
cp .env.example .env
# Éditer .env avec vos clés API (optionnel)
```

### Frontend
```bash
cd frontend
npm install
```

### Lancement
```bash
# Tout démarrer (backend port 8001 + frontend port 3001)
./start.sh

# Ou manuellement :
cd backend && python3 -m uvicorn app.main:app --port 8001 &
cd frontend && npx next dev -p 3001 &
```

### Arrêt
```bash
./stop.sh
```

## Configuration

Toute la configuration se fait depuis l'interface web sur `http://localhost:3001/settings` :

- Activer/désactiver chaque source individuellement
- Entrer les clés API nécessaires
- Régler l'intervalle de collecte automatique
- Définir le score de priorité minimum
- Configurer l'expiration des données obsolètes

## API

Le backend expose les endpoints suivants sur `http://localhost:8001` :

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/api/intelligence/items/` | Liste des éléments collectés |
| `GET` | `/api/intelligence/briefs/` | Résumés de renseignement |
| `GET` | `/api/intelligence/stats/` | Statistiques globales |
| `POST` | `/api/intelligence/collect` | Déclencher une collecte manuelle |
| `GET` | `/api/intelligence/config` | Configuration actuelle |
| `PUT` | `/api/intelligence/config` | Mettre à jour la configuration |

## Interface

L'interface est entièrement en **français** et comprend 4 pages :

- **Tableau de bord** : Vue d'ensemble avec signaux actionnables, résumés et alertes haute priorité
- **Flux brut** : Tous les éléments collectés avec filtres (catégorie, urgence, source)
- **Marchés** : Marchés Polymarket associés aux signaux détectés
- **Paramètres** : Configuration complète de toutes les sources

## Fonctionnement

Le scanner est **basé sur des règles** (rule-based) — pas de LLM. Il détecte des signaux via :

1. **Analyse de sentiment** (VADER) sur les titres et résumés
2. **Mots-clés prioritaires** par source (ex: "missile", "sanctions", "insider trade")
3. **Métriques d'engagement** (vues, score Reddit, nombre de commentaires)
4. **Crédibilité source** pondérée (SEC EDGAR = 1.0, Reddit = 0.4)
5. **Matching automatique** avec les marchés Polymarket via l'API Gamma

## Licence

Usage personnel uniquement.
