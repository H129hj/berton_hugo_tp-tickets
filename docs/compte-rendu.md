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

**Problème : premier déploiement de l'API en échec (`crashed-error`).**
J'ai créé l'app, ajouté l'addon PostgreSQL et lancé le déploiement juste après. Le build a réussi mais le conteneur plantait au démarrage. Les logs (`scalingo --app hugo-tickets-api logs --lines 40`) montraient `RuntimeError: DATABASE_URL est requis` : la base était encore en cours de création (« Database creation has started »), donc la variable `SCALINGO_POSTGRESQL_URL` n'existait pas encore quand l'API a démarré, et mon code refuse de démarrer sans URL de base.
**Résolution :** vérifier avec `scalingo --app hugo-tickets-api addons` que l'addon est passé en `running` et avec `env` que `SCALINGO_POSTGRESQL_URL` (et l'alias `DATABASE_URL`) est bien définie, puis relancer le déploiement. Le second déploiement est passé en `success` et `/health` a répondu `{"status":"ok"}`. À retenir : créer la base et attendre qu'elle soit prête avant le premier déploiement, et lire les logs avant de toucher au code.

**Autre problème : pas de Docker sur le poste en local.**
Le `docker-compose.yml` sert à lancer PostgreSQL, mais le démon Docker n'était pas lancé sur la machine.
**Résolution :** tests lancés sur un PostgreSQL 16 installé en local (`DATABASE_URL=postgresql:///tickets_test`). Comme toute la config passe par `DATABASE_URL`, rien n'a été changé dans le code.

## Vérifications faites

- 8 tests automatiques (création, liste, validation, changement de statut, statut invalide, 404, filtre et recherche, suppression).
- Parcours manuel dans le navigateur : création d'un ticket, passage en « en cours » puis « résolu », rechargement de la page, le ticket est toujours là.
- En production : création d'un ticket, passage en « en cours », statut invalide refusé (422), CORS limité à `https://h129hj.github.io`.
- Redéploiement : sous-titre de la page modifié, commit, push sur `main`, la GitHub Action a republié le frontend et la modification est visible en ligne sans action manuelle.
