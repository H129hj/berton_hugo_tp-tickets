# Compte rendu technique

## Choix d'hébergement

| Tier | Choix | Raison |
|---|---|---|
| Frontend | GitHub Pages | site statique, gratuit, HTTPS, redéployé par une GitHub Action à chaque push sur `main` |
| Backend | Scalingo (conteneur S) | voucher Ynov, déploiement automatique depuis GitHub, logs et rollback en CLI |
| Base | PostgreSQL, addon Scalingo Starter 512 | même région que l'API, URL injectée automatiquement, sauvegardes gérées |
| Code | GitHub | dépôt public, CI GitHub Actions |

## Principales configurations

- API : `Procfile` (`web: uvicorn main:app --host 0.0.0.0 --port $PORT`), version de Python fixée dans `api/.python-version`, dépendances figées dans `requirements.txt`.
- Monorepo : `PROJECT_DIR=api` sur l'app Scalingo pour que le buildpack construise le bon dossier.
- Variables d'environnement de l'API : `SCALINGO_POSTGRESQL_URL` (ajoutée par l'addon), `CORS_ORIGINS` (origine GitHub Pages).
- Frontend : la variable de dépôt `API_URL` est écrite dans `config.js` par le workflow `frontend.yml` au moment de la publication.
- URL de la base : l'addon peut la donner en `postgres://` alors que psycopg attend `postgresql://` ; `database_url()` dans `api/main.py` corrige le préfixe et accepte aussi `DATABASE_URL` (local et CI).
- Base : la table `tickets` est créée au démarrage de l'API depuis `schema.sql`, avec une contrainte `CHECK` sur le statut.
- CI : `api.yml` lance ruff et pytest contre un vrai PostgreSQL (service Docker de GitHub Actions) ; Scalingo ne déploie que si elle est verte.

## Problème rencontré et résolution

**Problème : pas de Docker sur le poste en local.**
Le `docker-compose.yml` sert à lancer PostgreSQL, mais le démon Docker n'était pas lancé sur la machine.
**Résolution :** tests lancés sur un PostgreSQL 16 installé en local (`DATABASE_URL=postgresql:///tickets_test`). Comme toute la config passe par `DATABASE_URL`, rien n'a été changé dans le code.

## Vérifications faites

- 8 tests automatiques (création, liste, validation, changement de statut, statut invalide, 404, filtre et recherche, suppression).
- Parcours manuel dans le navigateur : création d'un ticket, passage en « en cours » puis « résolu », rechargement de la page, le ticket est toujours là.
- Redéploiement : à faire une fois en ligne (modification visible du titre, commit, push, nouvelle version sans action manuelle).
