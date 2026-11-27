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
| `server-1000` | 1 000 graines, **temps d'exécution serveur** (`--server-timing`) — campagne publiée |
| `server-10000` | Idem, 10 000 graines — campagne publiée |
| `sql-fixes-1000` | Campagne corrigée après les correctifs SQL : les 18 méthodes passent |
| `fresh-install-1000` | Re-vérification sur installation neuve après consolidation |
| `consent-validation-1000` | 20 méthodes, dont retrait de consentement concurrent ; temps non retenus pour la performance |
| `attribute-ab-10000` | Comparaison A/B du prédicat d'attributs, 10 000 relations, échantillons, plans et sources de mesure |
| `attribute-ab3-10000` | **Campagne publiée** : trois écritures du prédicat d'attributs — décorrélée, corrélée, enveloppante — sur une même base durcie |
| `audit-cost-correlated` | **Campagne publiée** : coût du durcissement et du journal, une variable à la fois, avec le prédicat corrélé |
| `extended-evaluation` | 23 tests pour chacune des deux variantes ; rejeu clinique et correspondance finie |
| `expanded-run-1000` | Harnais complet : 23 méthodes réussies ; temps non retenus car travaux locaux simultanés |
| `correlated-1000` | **Campagne publiée** : prédicat d'attributs corrélé, build durci complet, 23 méthodes réussies |
| `correlated-10000` | Idem, 10 000 graines — campagne publiée |

[`migration-validation.log`](adam/migration-validation.log) consigne les
reconstructions historique et consolidée ainsi que l'installation neuve.

> Les campagnes `comparison/` antérieures au 24 novembre et la campagne `adam/audit-cost`
> précèdent la correction d'identité A01 : leur sujet venait d'une variable de session, que
> le durcissement ignore désormais. Elles restent conservées comme trace, mais seules les
> campagnes marquées « publiée » correspondent au code livré.

## `comparison/` — OpenFGA et SpiceDB

| Dossier | Campagne |
|---|---|
| `persistent-1000` | Comparaison rapportée dans l'article : stockages PostgreSQL et lecture de donnée sur les trois parcours |
| `persistent-hardened-1000` | **Campagne publiée** : même protocole, rejoué sur le build durci ; l'identité est résolue depuis les délégations enregistrées |

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

## Nouvelles campagnes

Les nouvelles mesures vont dans `Results/local/`, ignoré par git, afin de ne
jamais écraser les campagnes conservées. Ce dossier est absent d'une copie
fraîche : les lanceurs le créent.

```sh
uv run --group validation python Benchmark-AI/run.py --server-timing \
  --output Results/local/new-1000 --seeds 1000

uv run --group validation python NoSQL-PoC/run_mongo.py
```

Les lanceurs refusent un dossier contenant déjà des résultats. Les campagnes
conservées ici utilisent les sous-dossiers `1000`/`10000` ; une nouvelle
campagne MongoDB produit la même arborescence sous le dossier choisi.
