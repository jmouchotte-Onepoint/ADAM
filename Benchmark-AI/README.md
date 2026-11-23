# Reproducible SQL validation

> ## ⚠️ Partie produite par IA
>
> **L'intégralité de ce dossier — harnais de validation, tests, scripts de
> comparaison et rapports — a été produite par un assistant IA** et exécutée
> dans des environnements de test. Une revue par les auteurs reste nécessaire.
> Les résultats de ses exécutions sont conservés dans
> [`Results/`](../Results/README.md).
>
> Le cœur SQL ADAM (`ADAM/`), le générateur (`Examples/generator/`) et le
> modèle formel (`EventB/`) ne relèvent pas de cette partie.

This harness tests the SQL core and its generated
read policy, alongside a separately identified experimental RLS adapter in
`sql/fixture.sql`. It is not a deployed healthcare backend or a complete security
verification. All records are synthetic.

## Layout

```
run.py                       Runner principal (constantes BENCH / CHANGELOG / FIXTURE)
support.py                   Harnais partagé des tests
test_*.py                    Suites de tests base de données
check_liquibase_policy.py    Vérification de réapplication de politique
check_liquibase_migration.py Vérification de migration sur installations reconstituées
check_oauth_keycloak.py      Scénario OAuth/Keycloak
compare_authorization.py     Comparaison OpenFGA / SpiceDB
compare_persistent.py        Comparaison avec stockages persistants
compare_clinical.py          Rejeu comparatif synthétique T0--T4
compare_attribute_plans.py   Mesure A/B de l'évaluation des attributs
check_extended_evaluation.py Tests des deux variantes de l'adaptateur
fixtures/                    Archive historique pour la migration
sql/                         changelog.xml et fixture.sql
oauth/                       run_oauth.sh et oauth_claim_client.c
eventb/                      replay_eventb.sh
```

Les modules Python restent à plat : ils forment un espace de noms unique
(`from run import …`, `from support import …`) utilisé par la découverte
`unittest`.

## Testing strategy

- Type: database/configuration generator; no running HTTP or browser application.
- Infrastructure: real PostgreSQL 18.6 in Docker, one CPU, 1 GiB memory,
  random localhost port, no mounted or persistent volumes.
- Driver: Psycopg on the host. No SQLite fallback can validate PostgreSQL RLS.
- Legacy assets: no runnable test suite was found; the example bootstrap is
  unsuitable because it removes volumes and rewrites example files.
- Journeys: graph insertion/deletion; protected read/write with context changes;
  missing/wrong provisioned identity or tenant; expiration; committed revocation
  versus an older repeatable-read snapshot.
- Acceptance: actual visibility/persistence must match the assertions. A missing
  attribute is different from an SQL error. Failures return exit code 1.
- Scope gaps for this SQL suite: JWT validation, hostile session-setting
  changes, arbitrary SQL rules, all write paths, graph cycles, clinical
  governance, HTTP, Kubernetes, vault, and distributed behavior are not tested.
  The separate local OAuth experiment below covers a bounded Keycloak/JWT path.

The dedicated container uses local trust authentication to avoid stored test
passwords. This is only suitable for the disposable localhost-bound test
instance, never a production configuration. Its uniquely named container is
removed in `finally`; existing containers, volumes and SQL sources are untouched.

## Run

From the `Code` directory:

```sh
uv sync --group validation
uv run --group validation python Benchmark-AI/run.py --server-timing --output Results/local/new-1000 --seeds 1000
uv run --group validation python Benchmark-AI/run.py --server-timing --output Results/local/new-10000 --seeds 10000
```

Choose a new output directory for each run: the runner refuses to overwrite
existing result files. The published samples remain in `Results/adam/server-1000/`
and `Results/adam/server-10000/`.

The historical campaigns returned **1**: nine test methods passed, three
assertions failed and one method raised an SQL error. They reproduced:

1. Another provisioned subject can see a record through the generated policy.
2. An expired permission remains usable through the generated policy.
3. The unique role index accepts duplicates with a null parent.
4. The attribute wrapper references `attributes`, while the view exposes
   `attribute`.

The fixes remove the unconditional generated-policy branch and check candidate
expiry, correct the attribute wrapper, and add PostgreSQL `NULLS NOT DISTINCT`
unique indexes for roles and permissions. In the retained corrected 1,000-seed
run, **all 18 methods pass**, including the original regressions, regeneration
of the example policy, distinct parent paths and rejection of duplicate rows
with a null parent. That historical run used separate corrective migrations;
the current changelogs instead carry the fixes in the creation SQL itself.
See
[corrected test results](../Results/adam/sql-fixes-1000/results.json) and
[additional generator and test hashes](../Results/adam/sql-fixes-1000/source-hashes-extra.sha256).
The separate
adapter is still test-only and does not establish production guarantees.

The retained `source-hashes-extra.sha256` files record the generator paths as
they existed at measurement time; the generator has since been consolidated
into the `Examples/generator/` package. The [results index](../Results/README.md) gives
the path mapping and explains how each digest file resolves.

The original creation changesets retain the fixes and explicitly accept the
five identified historical checksums. The transactional changeset in
`ADAM/3a_MIGRATIONS/` replaces both unique indexes and reapplies the corrected
attribute wrapper. It was tested on complete reconstructed historical and
previously consolidated installations and a fresh installation, including
reapplication. Injected duplicate roles or permissions cause an atomic failure:
inspect and resolve duplicates deliberately; the migration never deletes them.
It is not a guarantee for partial or other historical versions. Back up the
database, inspect its Liquibase history and policies, test on a restored copy,
and plan for DDL locks before any real upgrade.

```sh
uv run --locked --group validation python Benchmark-AI/check_liquibase_migration.py
```

The script verifies the SHA-256 of `fixtures/adam-fe473fc.tar`, a source
snapshot from commit `fe473fcecd1f53d86d7d1142498b1c0103dfc932`, so the test
does not require Git history. Its [retained log](../Results/adam/migration-validation.log)
records the outcomes. PostgreSQL 18.6 was tested; `NULLS NOT DISTINCT` requires
PostgreSQL 15 or later, and the core uses `uuidv7()`, native in PostgreSQL 18.

The policy changeset is `runOnChange` and the supplied example SQL replaces
its named policy. Generate and review policies for the actual model and schema:
do not apply the Woodgrove example blindly to another database. Removed policy
definitions and unrelated existing policies require separate review.

To reproduce the bounded policy test:

```sh
uv run --group validation python Benchmark-AI/check_liquibase_policy.py
```

It reconstructs one historical example policy, installs it in an isolated
database, and tests that Liquibase reapplies the corrected policy and that the
authorized and unrelated subjects are decided correctly. It does not validate
every production configuration or a real existing database, and uses Docker
Desktop's `host.docker.internal`.

After an earlier consolidation, a [fresh-install rerun](../Results/adam/fresh-install-1000/results.json)
again passed all 18 methods, including verification that index creation rejects
existing duplicates. [Additional hashes](../Results/adam/fresh-install-1000/source-hashes-extra.sha256)
identify the test and generator sources. This rerun was a correctness check,
performed alongside other local work; its timings do not replace the historical
measurements.

To check reapplication of the example policy with Liquibase 4.32.0 against an
isolated PostgreSQL instance:

```sh
uv run --group validation python Benchmark-AI/check_liquibase_policy.py
```

This uses Docker Desktop's `host.docker.internal`; it verifies one reconstructed
historical policy changeset, not every deployment or migration path. Its
[retained log](../Results/adam/sql-fixes-1000/liquibase.log) records the successful run.

The nullable-index reproduction attempts a semantic duplicate directly; it does
not establish every recursive propagation path creates a duplicate.

## Local Keycloak / PostgreSQL OAuth experiment

This is a test-only identity integration, not the application backend. It uses
Keycloak 26.5.0 and PostgreSQL's native OAuth interface with the **pre-release**
[`pg_oauth_validator`](https://github.com/proddata/pg_oauth_validator) module.
The [Dockerfile](../Docker/OAuth.Dockerfile) pins the validator and its two source
dependencies to commits; operating-system packages are resolved at build time.
The observed run used PostgreSQL 18.7 and libpq 19.0 from the built image.
Only public dependency sources are downloaded during the build.

From `Code`, with Docker running and `uv` installed:

```sh
bash Benchmark-AI/oauth/run_oauth.sh
```

The [launcher](oauth/run_oauth.sh) builds a uniquely tagged image, runs the complete
scenario, and removes that tag. Docker may retain its build cache and downloaded
base images. The first build needs internet access and may take several minutes;
each run also waits for a test token to expire. The exit code is nonzero if
building, a scenario assertion, or cleanup fails.

The runner creates uniquely named disposable containers and a certificate volume,
generates a temporary CA and random test password, imports synthetic practitioners,
then removes those resources on normal completion or Python exceptions. Keycloak
runs in development mode with a password grant solely for this isolated test.
Its HTTPS port is published on a random localhost port; PostgreSQL is not
published to the host. After the command finishes the environment is no longer
running. A forcibly killed run may require manual cleanup of its uniquely named
`adam-oauth-*` resources.

The [test client](oauth/oauth_claim_client.c) supplies the access token to libpq's
OAuth hook. The database validator authenticates it before the client reads
its claims; the client also matches `sub` against PostgreSQL `system_user`.
It sets `sub`, `tenant_id`, and `profession` only within a read-only
transaction and tests the separate experimental RLS adapter. On commit it
checks that these settings are cleared, then closes the connection. Each test
uses a new connection, not a connection pool.

The passing run covered an assigned practitioner, different profession, tenant
or subject, missing profession or tenant, an unmapped subject, incorrect audience and
scope, a token from another realm, a modified signature, and expiration with
validator clock skew set to zero. A valid token was checked again after the
negative cases. The other realm has a different signing key as well as a
different issuer, so that case does not independently isolate issuer checking.
Results are correctness checks, not latency measurements.

**Trust boundary:** PostgreSQL session settings can be changed by a connected
SQL client. The prototype is safe to interpret only under its restricted local
boundary; it does not prevent an untrusted client with database access from
setting another identity or bypassing the test client. A real deployment must
restrict database access to its trusted service, prohibit arbitrary client SQL,
secure credential and network handling, and test its connection pool and
transaction cleanup. Token authentication occurs at connection time and is
not automatically repeated for a long-lived connection. Production suitability,
revocation behavior, deployment, full validator assurance, and all policy
configurations remain unproven.

## Benchmark

Each seed uses the existing triggers to create one relation, four roles and 21
permissions. Protected read/write permissions then receive one profession
attribute and one always-true SQL rule. This exercises the evaluation path,
not a representative range of clinical rules.

- Query workloads: one or four sessions; each targets a distinct fixed record;
  20 warm-ups then 100 measured operations; three repetitions.
- Measured paths: seed insertion, permission lookup, protected read, protected
  update and cascade deletion (100 sources).
- Clock: PostgreSQL `Execution Time` from `EXPLAIN (ANALYZE, BUFFERS,
  TIMING OFF, FORMAT JSON)`. It includes executor and trigger work, but not
  planning, network/client handling, or transaction commit. It includes
  instrumentation overhead and is not end-to-end latency.
- Data-modifying measured statements use `RETURNING id`; the plan must report
  exactly one returned row. Warm-ups verify that the lookup/read/write paths
  actually succeed.
- Recorded wall-clock throughput includes connections, warm-ups and EXPLAIN
  overhead; do not interpret it as steady-state maximum throughput.
- Percentiles: nearest rank. Per-repetition rows and raw samples are preserved.
- Existing indexes remain enabled; no index-only causal experiment is claimed.
  The service comparison below covers a different, limited workload.

`results.json` records settings, source hashes, image identity, suite counts,
failures and repetition-level latency summaries. `latencies.json` retains raw
samples; `plans.json` retains query plans. The historical overall FAIL status describes the original implementation-claim
tests, not loss or suppression of benchmark observations. Their source hashes
identify the pre-fix SQL; they must not be relabelled as post-fix measurements.

To regenerate the manuscript's measured table from completed runs, use the
exporter in [`Article-Export/`](../Article-Export/README.md). That directory is
deliberately excluded from git, so the command only works on a checkout that
still has it:

```sh
uv run --group validation python Article-Export/export_article.py \
  Results/adam/server-1000 Results/adam/server-10000 \
  --table ../Article/Table/Runtime-Benchmark.tex
```

The earlier `Results/adam/client-1000/` and `Results/adam/client-10000/` are retained separately:
their client-side times include driver/network handling and cannot be combined
with the server-side samples. Omitting `--server-timing` reproduces the earlier
client-clock protocol (300 measured operations per client and repetition).

There is no API to exercise with k6 in the supplied source. A future HTTP test
should measure a real backend and distinguish token authentication, policy
decision, data access, and network latency. The present harness does not invent
an endpoint to substitute for such evidence.

## OpenFGA and SpiceDB comparison

The runnable test and benchmark are in
[`compare_authorization.py`](compare_authorization.py); no separate service
installation is needed beyond Docker and the validation dependencies.
From the `Code` directory:

```sh
uv run --group validation python Benchmark-AI/compare_authorization.py \
  --output Results/local/new-comparison-1000 --seeds 1000
```

The retained [results](../Results/comparison/1000/results.json) and
[raw samples](../Results/comparison/1000/latencies.json) use PostgreSQL 18.6,
OpenFGA 1.14.1 and SpiceDB 1.57.1. All containers are disposable, restricted to
one CPU and 1 GiB, and bound to random localhost ports. The service stores are
in-memory; the local SpiceDB key is a disposable test value, not a production
credential. SpiceDB telemetry is disabled.

A [fresh-install rerun](../Results/comparison/fresh-1000/results.json) also passed the
decision checks after SQL consolidation. Other local work was running during
this check; use the retained comparison above for the manuscript's timings.

The common subset is one synthetic direct assignment per record and an allowed
read; checks also verify other subject, absent record, a different tenant
identifier, and committed revocation. Tenant identity is encoded in the
external systems' resource IDs, not implemented as a general tenant model.
PostgreSQL uses the generated RLS policy, materialized permissions and a
record lookup. The other systems return authorization decisions without an
application-data lookup. PostgreSQL uses its database protocol and
READ COMMITTED; the services use persistent HTTP/JSON connections with
HIGHER_CONSISTENCY and fullyConsistent respectively. One and four clients each
perform 20 warm-ups, then 100 checks, in three repetitions; pooled p50/p95/p99
use nearest rank. Measurements include local client/protocol time.

The three executions have different storage, durability, policy richness,
protocols, and internal caches. They do not compare equivalent clinical
workloads or support a general speedup claim.

The manuscript additionally reports the stronger persistent-store experiment:

```sh
uv run --locked --group validation python Benchmark-AI/compare_persistent.py \
  --output Results/local/persistent-1000 --seeds 1000
```

Its [results](../Results/comparison/persistent-1000/results.json) and
[samples](../Results/comparison/persistent-1000/latencies.json) use separate
PostgreSQL databases for both service stores and application data. All measured
paths include a record lookup. The shared PostgreSQL container has no persistent
volume and its databases are discarded after the run. ADAM applies RLS; each service path checks over
HTTP and then reads an unrestricted table using a trusted client. These steps
are not atomic and the trust boundaries differ. One and four clients, 20
warm-ups, 100 operations per client and three repetitions are used; the runs
are sequential. Different models, protocols, caches, resource contention, and
transaction/consistency guarantees prevent a general ranking. Persistent
storage does not by itself prove equivalent durability.

The same command now also runs a [synthetic pathway projection](../Results/comparison/clinical-replay-1000/results.json):
11 expected decisions at T0--T4 and negative controls are checked against the
experimental SQL adapter and both service APIs. For OpenFGA/SpiceDB the driver
explicitly adds/removes direct tuples when state changes; it does not establish
automatic expiry, production synchronization, atomic authorization plus data
access, or a full clinical workflow. The SQL test uses a provisioned emergency
attribute, a generic record consent flag and source expiry. These decision
checks do not form the timed record-read benchmark. At T3 the test explicitly
sets the source expiration to a past timestamp instead of waiting for a real
delegation window to elapse.

## Attribute evaluation A/B experiment

```sh
uv run --locked --group validation python Benchmark-AI/compare_attribute_plans.py \
  --seeds 10000 --samples 30 --output Results/local/attribute-ab-10000
uv run --locked --group validation python Benchmark-AI/check_extended_evaluation.py \
  --output Results/local/extended-evaluation.json
```

The [retained samples and plans](../Results/adam/attribute-ab-10000/results.json)
compare the original experimental adapter predicate with an otherwise identical
policy calling the existing attribute wrapper on a selected permission. Both
run sequentially on the same database, baseline first: one/four clients, 10
warm-ups, 30 measured operations per client, three repetitions, with
`EXPLAIN ANALYZE TIMING OFF`. At 10,000 relations the baseline plan scanned
permission attributes broadly; the targeted candidate was markedly faster in
this workload. This is not a production or general performance claim.

The [extended checks](../Results/adam/extended-evaluation/results.json) ran 23
methods against each variant, including local/inherited attributes, a
simplified pathway, and a finite Event-B-inspired SQL correspondence.
The wrapper is `SECURITY DEFINER`; privileges, its behavior under all
constraint combinations and search-path assumptions need a security review.
The production policies are not changed by this experiment. The
`measurement-source/` snapshot preserves the helper files used for the A/B run;
the current benchmark adds start-time and source-hash provenance.

The finite correspondence assumes empty data metadata, subject-identifying
authorization metadata, explicit record/operation scopes and tenant-consistent
provisioned identities. Its hand-derived oracle is compared with SQL over 32
subject/record/operation combinations and one post-revocation read. SQL updates
are modeled as requiring both read and write scopes. This does not execute
Rodin as an oracle, prove SQL refinement, or validate untrusted claims.

## Event-B replay

```sh
bash Benchmark-AI/eventb/replay_eventb.sh /tmp/adam-eventb-new-replay
```

The script packages only source files and runs a digest-pinned rodin-headless
5.0 image with network disabled. It records source hashes, the Rodin log and
the rebuilt archive. In the [retained replay](../Results/eventb/replay/rodin.log),
all six components passed static checking and all generated obligations were
discharged: eight for `M1_Adam`, four each for two contexts, and none for the
remaining three components. This does not prove SQL refinement or liveness.
The image uses x86-64 emulation on an arm64 host.
Use a new local output directory for each run; synchronised folders can time
out while Rodin writes its archive and log.

## MongoDB prototype and comparison

The separate [NoSQL proof of concept](../NoSQL-PoC/README.md) contains its own
adapter, tests, runner and MongoDB samples. Its documentation explains the
different enforcement boundary and why these measurements cannot be used to
calculate a general SQL-versus-MongoDB speedup.
