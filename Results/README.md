# Résultats de mesure

Toutes les campagnes conservées, regroupées hors des dossiers de code. Le code
qui les produit est dans [`Benchmark-AI/`](../Benchmark-AI/README.md) (PostgreSQL,
comparaison, Event-B) et [`NoSQL-PoC/`](../NoSQL-PoC/README.md) (MongoDB).

## Contenu des dossiers

| Fichier | Contenu |
|---|---|
| `results.json` | Paramètres, empreintes des sources, résultats des tests, synthèse des répétitions |
| `latencies.json` | Échantillons de latence bruts |
| `plans.json` | Plans d'exécution PostgreSQL (`EXPLAIN ANALYZE`) |
| `source-hashes*.sha256` | Empreintes complémentaires des sources |
| `liquibase.log` | Trace Liquibase conservée |

### Résolution des chemins dans les `.sha256`

- `eventb/replay/source-hashes.sha256` et `reruns/eventb-replay/…` : chemins
  relatifs au dossier [`EventB/`](../EventB/) (produits depuis celui-ci).
- `adam/*/source-hashes-extra.sha256` : chemins relatifs à la racine `Code/`.
  Deux entrées datent d'avant le regroupement du générateur et se lisent ainsi :

  | Chemin enregistré | Chemin actuel |
  |---|---|
  | `init_archi_rls_sql.py` | `Examples/generator/models.py` |
  | `Resources/write_sql.py` | `Examples/generator/write_sql.py` |

  Les empreintes décrivent toujours le contenu au moment de la campagne ; seuls
  les emplacements ont changé.

## `adam/` — cœur SQL ADAM sur PostgreSQL

| Dossier | Campagne |
|---|---|
| `client-1000` | Première campagne, 1 000 graines, **horloge client** |
| `client-10000` | Idem, 10 000 graines |
| `server-1000` | 1 000 graines, **temps d'exécution serveur** (`--server-timing`) — campagne publiée |
| `server-10000` | Idem, 10 000 graines — campagne publiée |
| `sql-fixes-1000` | Campagne corrigée après les correctifs SQL : les 18 méthodes passent |
| `fresh-install-1000` | Re-vérification sur installation neuve après consolidation |
| `consent-validation-1000` | 20 méthodes, dont retrait de consentement concurrent ; temps non retenus pour la performance |
| `attribute-ab-10000` | Comparaison A/B du prédicat d'attributs, 10 000 relations, échantillons, plans et sources de mesure |
| `extended-evaluation` | 23 tests pour chacune des deux variantes ; rejeu clinique et correspondance finie |
| `expanded-run-1000` | Harnais complet : 23 méthodes réussies ; temps non retenus car travaux locaux simultanés |

[`migration-validation.log`](adam/migration-validation.log) consigne les
reconstructions historique et consolidée ainsi que l'installation neuve.

## `comparison/` — OpenFGA et SpiceDB

| Dossier | Campagne |
|---|---|
| `1000` | Comparaison conservée, 1 000 graines, PostgreSQL 18.6 |
| `fresh-1000` | Re-exécution sur installation neuve |
| `persistent-1000` | Comparaison rapportée dans l'article : stockages PostgreSQL et lecture de donnée sur les trois parcours |
| `clinical-replay-1000` | Onze décisions synthétiques T0--T4 comparées ; données de latence séparées de la campagne publiée |

## `mongodb/` — prototype NoSQL

| Dossier | Campagne |
|---|---|
| `1000` | 1 000 documents — campagne publiée |
| `10000` | 10 000 documents — campagne publiée |
| `fresh-validation/{1000,10000}` | Re-vérification |

## `eventb/` — modèle formel

| Dossier | Campagne |
|---|---|
| `replay` | Rejeu Rodin conservé (`rodin.log`, archive reconstruite) |

## `reruns/` — re-exécutions conservées

Vérifications internes, **non citées** dans l'article. Conservées comme trace
de travail ; supprimables sans impact sur les références documentaires.

| Dossier | Campagne |
|---|---|
| `adam-migrated-1000` | Campagne sur une base migrée (chemin de migration depuis retiré) |
| `adam-sql-fixes-1000` | Re-exécution des correctifs SQL |
| `adam-sql-fixes-1000-v2` | Seconde re-exécution |
| `eventb-replay` | Re-exécution du rejeu Rodin |
| `review-2026-11-23` | Revalidation SQL et comparaison à 1 000 graines, MongoDB aux deux tailles et échec de compatibilité Liquibase sur base historique reconstituée |

La revalidation du 23 novembre utilise des exécutions parallèles pour les
vérifications SQL et la comparaison : ses temps ne remplacent pas les
campagnes publiées. Les mesures MongoDB ont été relancées après correction du
lanceur ; les empreintes des scripts figurent dans les résultats. Le journal
Liquibase montre le refus des cinq checksums modifiés, et non une migration
réussie.

## Nouvelles campagnes

Les nouvelles mesures vont dans `Results/local/`, ignoré par git, afin de ne
jamais écraser les campagnes conservées :

```sh
uv run --group validation python Benchmark-AI/run.py --server-timing \
  --output Results/local/new-1000 --seeds 1000

uv run --group validation python NoSQL-PoC/run_mongo.py
```

Les lanceurs refusent un dossier contenant déjà des résultats. Les campagnes
conservées ici utilisent les sous-dossiers `1000`/`10000` ; une nouvelle
campagne MongoDB produit la même arborescence sous le dossier choisi.
