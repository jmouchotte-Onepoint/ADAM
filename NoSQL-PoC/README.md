# Prototype NoSQL : MongoDB

Ce dossier contient une adaptation expérimentale de certaines décisions
d'accès ADAM, et non une conversion complète du modèle SQL :

- `mongo_adapter.py` : lecture et écriture protégées sur un document ;
- `test_mongo_adapter.py` : huit tests des décisions et des refus ;
- `run_mongo.py` : lancement du conteneur, des tests et des mesures.

Les résultats sont regroupés hors de ce dossier, dans
[`Results/mongodb/`](../Results/mongodb/) : `1000/` et `10000/` sont les
campagnes utilisées dans l'article, `fresh-validation/` une re-vérification.
Voir l'[index des campagnes](../Results/README.md).

## Lancement

Prérequis : Docker en fonctionnement, Python 3.10+ et `uv`. Depuis le dossier
`Code` :

```sh
uv sync --group validation
uv run --group validation python NoSQL-PoC/run_mongo.py
```

Le programme crée un conteneur MongoDB temporaire, accessible uniquement sur un
port localhost aléatoire, puis exécute les tests et les deux campagnes. Il
supprime uniquement son propre conteneur. Les nouvelles mesures sont placées
dans un sous-dossier unique de `Results/local/` : elles n'écrasent pas les
résultats de l'article. Pour choisir un autre emplacement :

```sh
uv run --group validation python NoSQL-PoC/run_mongo.py --output /chemin/vers/nouvelle-campagne
```

Le programme refuse un emplacement contenant déjà les dossiers de résultats
de la campagne et interrompt les mesures si aucun test n'est découvert. La
base temporaire est sans authentification : elle ne doit
jamais recevoir de données réelles. En cas d'import manquant dans VS Code,
sélectionner l'interpréteur `Code/.venv` créé par `uv sync`.

## Périmètre

Chaque document synthétique contient un tenant, le consentement, quatre
étiquettes de rôles non utilisées et 21 permissions intégrées, dont une pour
la lecture et une pour l'écriture. Le filtre vérifie l'identité, le tenant,
l'opération, la profession, le consentement, la validité de la permission et
de sa source, ainsi que leurs dates d'expiration. Une mise à jour nécessite
les permissions de lecture et d'écriture. La vérification et l'opération sont
effectuées sur le même document.

Les huit tests couvrent les accès autorisés, les différences de sujet, tenant
et profession, les entrées absentes, le consentement, l'expiration et la
révocation dans un document. Les entrées absentes déclenchent une erreur.
L'adaptateur n'implémente pas le calcul récursif, les règles SQL dynamiques,
la révocation entre documents ni un service authentifié. En production, des
accès directs à la collection pourraient contourner le filtre ; un service
de confiance et des droits limités restent nécessaires.

## Mesures et comparaison

Les résultats publiés utilisent MongoDB 8.0.38, un CPU, 1 Gio de mémoire et
un cache WiredTiger de 0,25 Gio. Chaque campagne comporte 1 000 ou 10 000
documents et un ou quatre clients : 20 opérations d'échauffement, puis 100
mesures par client, sur trois répétitions. Le temps provient du profileur
MongoDB `system.profile.millis`, pas de Python. Sa résolution est d'une
milliseconde : une valeur affichée à 0 ne signifie pas une durée nulle.

Les mesures PostgreSQL du dossier [Benchmark](../Benchmark-AI/README.md) utilisent
`EXPLAIN ANALYZE`, des vues et règles SQL et une politique RLS expérimentale.
Le périmètre, l'instrumentation et les garanties de durabilité ne sont pas
équivalents ; aucun facteur d'accélération général ne peut être déduit.

Les fichiers `results.json` historiques conservent les empreintes des scripts
ayant produit les mesures de l'article. La version d'origine du lanceur est
conservée dans `measurement-source/run_mongo.py` pour vérifier son empreinte ;
elle ne sert pas au lancement actuel et n'est volontairement pas modifiée, ce
qui explique qu'elle écrive encore dans des dossiers `results-mongo-*`. Les
traces SQL historiques peuvent de même mentionner l'ancien chemin
`validation/`, qui était correct lors de leur exécution.
