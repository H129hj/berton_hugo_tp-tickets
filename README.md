# Support informatique - application de tickets

Petite application web qui permet aux collaborateurs de déclarer un incident informatique, de consulter les demandes et de suivre leur résolution (statuts **Ouvert**, **En cours**, **Résolu**).

TP Mise en production & Hébergement, Ynov B2.

## Liens

| | URL |
|---|---|
| Frontend | https://h129hj.github.io/berton_hugo_tp-tickets/ |
| API | https://hugo-tickets-api.osc-fr1.scalingo.io |
| Santé de l'API | https://hugo-tickets-api.osc-fr1.scalingo.io/health |
| Documentation de l'API (Swagger) | https://hugo-tickets-api.osc-fr1.scalingo.io/docs |

## Architecture

Architecture trois tiers : le navigateur charge le frontend statique, qui appelle l'API en HTTPS. Seule l'API parle à la base.

```mermaid
flowchart LR
    U[Navigateur] -- HTTPS : pages --> F[Frontend HTML/CSS/JS<br/>GitHub Pages]
    U -- HTTPS : fetch JSON --> A[API FastAPI<br/>Scalingo, conteneur S]
    A -- SQL --> D[(PostgreSQL<br/>addon Scalingo Starter 512)]
    G[Dépôt GitHub] -- push sur main --> F
    G -- push sur main, CI verte --> A
```

Détail et justification des choix : [docs/architecture.md](docs/architecture.md). Compte rendu technique : [docs/compte-rendu.md](docs/compte-rendu.md).

| Tier | Techno | Hébergement |
|---|---|---|
| Frontend | HTML, CSS, JavaScript (fetch) | GitHub Pages |
| Backend | Python 3.12, FastAPI, psycopg 3 | Scalingo |
| Base de données | PostgreSQL 16 | Addon PostgreSQL Scalingo |
| Code source | Git | GitHub |

## Fonctionnalités

- F1 liste des tickets (titre, description, statut, priorité, date de création)
- F2 création d'un ticket (titre + description, priorité facultative)
- F3 changement de statut : ouvert, en cours, résolu
- F4 persistance en base PostgreSQL
- F5 frontend et API en ligne en HTTPS
- Bonus : suppression, filtre par statut, recherche par mot-clé, priorité, date de création

## API

| Méthode | Route | Rôle | Codes |
|---|---|---|---|
| GET | `/health` | vérifie que l'API et la base répondent | 200, 503 |
| GET | `/api/tickets?statut=&q=` | liste des tickets (filtre et recherche facultatifs) | 200 |
| POST | `/api/tickets` | crée un ticket `{titre, description, priorite?}` | 201, 422 |
| PATCH | `/api/tickets/{id}` | change le statut `{statut}` | 200, 404, 422 |
| DELETE | `/api/tickets/{id}` | supprime un ticket | 204, 404 |

Les données reçues sont validées par Pydantic (titre et description non vides, longueur maximale, statut et priorité parmi les valeurs permises). La base contrôle aussi les statuts avec une contrainte `CHECK`.

## Lancer en local

Prérequis : Python 3.12 et un PostgreSQL (le `docker-compose.yml` en fournit un sur le port 5433).

```bash
docker compose up -d

cd api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env            # puis exporter les variables
export DATABASE_URL=postgresql://tickets:tickets@localhost:5433/tickets
export CORS_ORIGINS=http://localhost:5500
uvicorn main:app --reload --port 8000

# dans un autre terminal
cd frontend
python -m http.server 5500      # http://localhost:5500
```

La table `tickets` est créée au démarrage de l'API à partir de `api/schema.sql` (`CREATE TABLE IF NOT EXISTS`).

Tests : `cd api && pytest` (il faut une base de test dans `DATABASE_URL`, elle est vidée par les tests).

## Variables d'environnement

| Variable | Où | Rôle |
|---|---|---|
| `DATABASE_URL` ou `SCALINGO_POSTGRESQL_URL` | API | connexion à PostgreSQL (fournie par l'addon sur Scalingo) |
| `CORS_ORIGINS` | API | origines autorisées, séparées par des virgules (l'URL du frontend en prod) |
| `PORT` | API | port d'écoute, fourni par Scalingo |
| `API_URL` | frontend | URL publique de l'API, écrite dans `config.js` au déploiement |

Aucune valeur secrète n'est dans le dépôt : `.env` est ignoré par Git et l'URL de la base ne vit que dans les variables de Scalingo.

## Déploiement

### Base de données et API (Scalingo)

```bash
scalingo create hugo-tickets-api
scalingo --app hugo-tickets-api addons-add postgresql postgresql-starter-512
scalingo --app hugo-tickets-api env-set PROJECT_DIR=api
scalingo --app hugo-tickets-api env-set CORS_ORIGINS=https://h129hj.github.io
```

Puis dans le dashboard Scalingo, onglet Deploy : lier le dépôt GitHub, branche `main`, et activer **Auto Deploy**. `PROJECT_DIR=api` dit au buildpack Python de construire le dossier `api/` (sans ça il cherche `requirements.txt` à la racine). Le `Procfile` lance `uvicorn main:app --host 0.0.0.0 --port $PORT`.

Vérification : `curl https://hugo-tickets-api.osc-fr1.scalingo.io/health` renvoie `{"status":"ok"}`, et les logs se lisent avec `scalingo --app hugo-tickets-api logs --lines 100`.

### Frontend (GitHub Pages)

Le workflow `.github/workflows/frontend.yml` publie le dossier `frontend/` sur GitHub Pages à chaque push sur `main`. Il écrit `config.js` avec l'URL de l'API, prise dans la variable de dépôt `API_URL` (Settings > Secrets and variables > Actions > Variables).

### Redéploiement automatique

Un push sur `main` :
1. lance la CI (`api.yml` : ruff + pytest avec un PostgreSQL de test) ;
2. redéploie le frontend sur GitHub Pages ;
3. redéploie l'API sur Scalingo, qui attend que la CI soit verte.

## Coût

Frontend gratuit (GitHub Pages). API : un conteneur S et un addon PostgreSQL Starter 512 sur Scalingo, pris sur le voucher Ynov. Les ressources sont à supprimer après la soutenance.
