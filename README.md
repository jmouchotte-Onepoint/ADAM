# ADAM — Authorization Data & Access Model

ADAM est un moteur d'autorisation basé sur PostgreSQL qui combine **ReBAC**
(relations), **RBAC** (rôles), **RUBAC** (règles) et **ABAC/CBAC**
(attributs/contexte) dans un seul modèle de permissions multi-tenant.

À partir d'une description YAML du domaine (types d'objets, relations, rôles,
règles, tenants), ADAM génère le SQL nécessaire pour :

- créer le schéma d'autorisation (`relations`, `roles`, `permissions`, `model`, `tenants`, …) ;
- peupler les politiques Row-Level Security (RLS) et les règles SQL dynamiques ;
- initialiser des relations/rôles pour le développement et les tests.

## Prérequis

- **Python 3.10+**
- **[uv](https://docs.astral.sh/uv/)** pour les dépendances et l'exécution
- **Docker** et **Docker Compose** (PostgreSQL + Liquibase en local)

```bash
uv sync
```

## Organisation du dépôt

```
ADAM/                 Changelogs Liquibase, appliqués par couches (voir ci-dessous)
Examples/             Exemples + le générateur Python (YAML → SQL)
Docker/               Images et scripts d'init PostgreSQL
Benchmark-AI/         Code de validation produit par IA (tests, comparaison, Event-B)
NoSQL-PoC/            Code du prototype MongoDB
Results/              Campagnes de mesure conservées (tous sujets confondus)
EventB/               Sources du modèle formel (Rodin)
Article-Export/       Production des livrables du manuscrit (non versionné)
main.py               Point d'entrée CLI
example.sh            Bootstrap complet d'un exemple via Docker
docker-compose.yml    Services postgres + liquibase
```

Trois séparations structurent le dépôt :

- **code et sorties** : `Benchmark-AI/` et `NoSQL-PoC/` ne contiennent que du
  code, toutes les campagnes conservées sont dans [`Results/`](Results/README.md) ;
- **autorat** : `Benchmark-AI/` signale que cette partie a été produite par IA,
  contrairement au cœur SQL, au générateur et au modèle formel ;
- **versionné et hors dépôt** : [`Article-Export/`](Article-Export/) (livrables
  du manuscrit) et `Results/local/` (mesures locales) sont exclus de git.

Le paquet `Examples/generator/` :

| Module | Rôle |
|---|---|
| `models.py` | Modèle, politiques RBAC/RUBAC, RLS, tenants et règles dynamiques |
| `relations.py` | Jeux de relations/rôles pour le dev et les tests |
| `write_sql.py` | Construction des instructions SQL |
| `files.py` | Lecture YAML et gestion des fichiers de sortie |
| `utils.py` | Échappement et conversion des valeurs SQL |

### Les couches du changelog (`ADAM/changelog.xml`)

Liquibase applique les changelogs dans cet ordre, chaque couche s'appuyant sur
la précédente :

| Couche | Dossier | Rôle |
|---|---|---|
| 0 | `0_INIT` | Création du schéma de base, table `tenants`, utilisateurs initiaux |
| 1 | `1_REBAC_RBAC` | Modèle relationnel, tables `relations`/`roles`/`permissions`, fonctions, triggers, politiques |
| 2 | `2_RUBAC` | Règles SQL dynamiques attachées aux relations/rôles/permissions |
| 3 | `3_ABAC_CBAC` | Conditions sur attributs/contexte au-dessus de RBAC/RUBAC |
| 4 | `4_INSERT` | SQL généré par `main.py --models` (modèle, politiques, RLS, tenants, règles) |
| 5 | `5_DEV_TEST` | Données de dev/test propres à l'exemple, appliquées uniquement avec le contexte `dev` |
| 6 | `6_AUDIT_TRAIL` | Journal des écritures d'autorisation, en ajout seul et chaîné par tenant |
| 7 | `7_SECURITY` | Invariants transverses : `search_path` figé sur les fonctions du schéma |

## Démarrage rapide

`example.sh` enchaîne tout : copie des fichiers d'init de l'exemple, génération
du SQL depuis son YAML, puis démarrage de PostgreSQL + Liquibase.

```bash
sh example.sh <NomExemple> [schema_cible]
```

- `<NomExemple>` — un dossier de `Examples/` (`Contoso`, `Fabrikam`, `Tailspin`, `Woodgrove`).
- `[schema_cible]` — schéma PostgreSQL utilisé comme `search_path` par défaut (`adam` si omis).

```bash
sh example.sh Woodgrove
```

Ce script va :

1. détruire la pile précédente (`docker compose down -v`) ;
2. copier `Examples/Woodgrove/Database/docker-entrypoint-initdb.d/*` et
   `Examples/Woodgrove/Database/adam-entrypoint-dev-test.d/*` vers les dossiers d'init locaux ;
3. exécuter `main.py --models` puis `main.py --relations` sur les YAML de l'exemple ;
4. lancer `docker compose up -d` (PostgreSQL + Liquibase, toutes les couches y compris `5_DEV_TEST`).

Vérifier le résultat de la migration :

```bash
docker compose logs liquibase
```

> **Attention** : `example.sh` supprime des volumes Docker et réécrit les
> fichiers générés dans `ADAM/4_INSERT/` et `ADAM/5_DEV_TEST/`. Pour une
> validation isolée, utiliser les commandes du [benchmark](Benchmark-AI/README.md),
> qui n'utilisent pas ce script.

## Référence CLI (`main.py`)

`main.py` lit la configuration YAML et écrit les fichiers SQL. Il ne se
connecte jamais à la base : les `.sql` produits sont repris par les changelogs
Liquibase décrits plus haut.

### `--models <chemin/vers/init-models.yml>`

Génère la définition du modèle, les politiques RBAC/RUBAC, les politiques RLS,
les tenants et les règles dynamiques.

```bash
uv run ./main.py --models ./Examples/Woodgrove/init-models.yml
```

Sorties :

- `./ADAM/4_INSERT/INSERT-MODEL-POLICY.sql`
- `./ADAM/4_INSERT/INSERT-MODEL-POLICY-RULES.sql`
- `./ADAM/4_INSERT/INSERT-RLS-POLICY.sql`
- `./ADAM/4_INSERT/INSERT-TENANTS.sql`
- `./ADAM/4_INSERT/INSERT-DYNAMIC-RULES.sql`

### `--relations <chemin/vers/dev-init-relations.yml>`

Génère les données d'initialisation (relations et rôles) du modèle ReBAC.

```bash
uv run ./main.py --relations ./Examples/Woodgrove/dev-init-relations.yml
```

Sortie :

- `./ADAM/5_DEV_TEST/ADAM-0001-ADD-RELATIONS.sql`

> Ce fichier doit être référencé depuis le `changelog.xml` de l'exemple (sous
> `Database/adam-entrypoint-dev-test.d/`) pour que Liquibase le prenne en
> compte avec le contexte `dev`.

## Configuration YAML

Chaque exemple fournit deux fichiers :

- **`init-models.yml`** — définit `tenants`, `models` (types d'objets, leurs
  `relations`/`roles`/`permissions` et les `policy`/`rules` associées), et
  éventuellement des `rules` globales (conditions SQL nommées et paramétrées,
  réutilisables entre politiques).
- **`dev-init-relations.yml`** — définit, par tenant, une liste de triplets
  `user` / `relation` / `object` (optionnellement `type: roles`) pour peupler le
  graphe ReBAC en développement et en test manuel.

Voir [Examples/README.md](Examples/README.md) pour une présentation annotée.

## Validation scientifique

- [ADAM](ADAM/) : SQL et changelogs de création.
- [Benchmark](Benchmark-AI/README.md) : tests SQL, comparaison exécutable avec
  OpenFGA et SpiceDB, rejeu Event-B et commandes de reproduction.
- [NoSQL-PoC](NoSQL-PoC/README.md) : prototype MongoDB et ses tests.
- [Results](Results/README.md) : index des campagnes de mesure conservées.

Pour lancer le scénario complet Keycloak, OAuth PostgreSQL et ADAM, depuis
`Code` avec Docker et `uv` :

```bash
bash Benchmark-AI/oauth/run_oauth.sh
```

Le scénario utilise uniquement des données synthétiques et arrête ses
conteneurs à la fin. Voir les [détails et limites](Benchmark-AI/README.md#local-keycloak--postgresql-oauth-experiment).

Les correctifs des index (`NULLS NOT DISTINCT`) et du wrapper d'attributs sont
intégrés dans les fichiers de création et un changeset transactionnel permet la
migration des installations complètes reconstituées testées. Sauvegarder et
contrôler l'historique, les doublons et les verrous avant toute migration réelle.
Les tests sont limités et ne certifient pas la sécurité en production ; voir le
[benchmark](Benchmark-AI/README.md).

## Préparation de la diffusion

Le supplément local rassemble le code, les fixtures historiques, le modèle
Event-B, les résultats et les commandes de reproduction. Avant publication,
les auteurs doivent contrôler son contenu et les droits de diffusion, puis
publier une version figée accessible sans authentification et reporter son
identifiant et son lien dans le manuscrit. La présence locale des fichiers ne
constitue pas une publication. Le dossier `Article-Export/` est inclus dans
le supplément local mais reste exclu du dépôt Git actuel.
