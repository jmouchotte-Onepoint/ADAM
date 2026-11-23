# Runtime validation report

## Current status after targeted fixes

The [expanded 1,000-seed runner](../Results/adam/expanded-run-1000/results.json)
passed 23 test methods with exit code 0. Its timing samples were collected
alongside local work and are not the manuscript's performance campaign.
The [extended checks](../Results/adam/extended-evaluation/results.json) passed
the same 23 methods for both the original adapter and the experimental
targeted-wrapper variant. These tests include a restricted synthetic clinical
replay and a finite model-inspired SQL comparison, not a clinical trial or SQL
refinement proof.

The [migration test](../Results/adam/migration-validation.log) passed for
complete historical and consolidated reconstructions and a fresh installation,
including duplicate-conflict recovery and reapplication. It is not assurance
for an arbitrary production installation. The
[OpenFGA/SpiceDB clinical projection](../Results/comparison/clinical-replay-1000/results.json),
[attribute A/B experiment](../Results/adam/attribute-ab-10000/results.json) and
[Rodin replay](../Results/eventb/replay/rodin.log) are retained with their
limitations and reproduction commands in the [README](README.md).

Current validation verdict: Docker available (`docker info`); Node.js v24.14.1
available; browser tier skipped because no runnable browser application is in
scope. PostgreSQL startup and schema loading: PASS; expanded integration suite:
PASS (exit 0, 23 passed, none skipped); browser E2E: UNVERIFIED. Overall:
NEEDS SIGNOFF for the untested production, identity, security and clinical
boundaries. The remainder documents the **historical pre-fix campaign**.

## Historical report: before fixes

**Evidence timestamp:** 2026-11-23T09:04:57Z (completed 1,000-seed run).
**Target:** supplied ADAM PostgreSQL core and a separate synthetic RLS adapter.
**Overall: FAIL.** This is an evidence report, not production acceptance.

The original client-clock observations below are retained for transparency.
The manuscript now uses the separate PostgreSQL server-side runs described in
the section "PostgreSQL execution-time benchmark".

## Summary

| Step | Status | Exit code | Evidence |
|---|---|---|---|
| PostgreSQL startup and SQL loading | PASS | 0 | Real PostgreSQL 18.6; TCP readiness and successful connections |
| Experimental protected-access adapter | PASS | 0 | Four test methods |
| Source insertion/deletion lifecycle | PASS | 0 | Three test methods |
| Ordered concurrent revocation | PASS | 0 | Two test methods |
| Existing repository claims | FAIL | 1 | Three assertion failures, one SQL error |
| Complete 1,000-seed runner | FAIL | 1 | Benchmark retained despite failed correctness claims |
| Complete 10,000-seed runner | FAIL | 1 | Same test counts; benchmark completed and retained |
| HTTP/browser E2E | UNVERIFIED | n/a | No runnable backend/browser application supplied |

Thirteen methods ran: nine passed, three failed, one raised an error; none were
skipped or marked as expected failures. The original SQL was not repaired.
Passing adapter tests do not establish that the generated production policy
enforces the same conditions.

## Environment and strategy

- Docker CLI and daemon: available, verified with `docker info`.
- Node.js: available, v24.14.1. Browser tooling is not applicable to this
  database/configuration-generator target; Playwright was not installed.
- Infrastructure tier: primary, real PostgreSQL 18.6 in Docker, not an
  in-memory fallback.
- Browser tier: skipped because there is no rendered application.
- Host: Apple M4 arm64, 16 GiB memory; Python 3.14.3 and Psycopg 3.3.9.
- Container: one CPU, 1 GiB memory, ephemeral localhost port, no mounted or
  persistent volume; only the uniquely named validation container is removed.
- Image: `sha256:74935e72241653ca55e0414067e6d8763aceb8a810eb51b452253ec3dcfc4336`.
- Database durability: `fsync=on`, `synchronous_commit=on`;
  `shared_buffers=128 MiB`, `work_mem=4 MiB`.
- Local trust authentication is disposable-test infrastructure only. Identity
  claims are provisioned session values, not cryptographically validated JWTs.
- No runnable legacy test suite was found. The destructive example bootstrap
  was deliberately not executed. Four new unittest files exercise setup,
  action, state/visibility verification, and cleanup.

The initial readiness probe was corrected to avoid PostgreSQL's temporary
initialization server. The experimental attribute bridge was corrected after
observing lowercase view discriminators and the singular `attribute` column.
These were test-harness fixes, not silent repairs to the supplied core.

## Reproduction and retained evidence

From the parent `Code` directory:

```sh
uv sync --group validation
uv run --group validation python Benchmark-AI/run.py \
  --output Results/local/new-client-1000 --seeds 1000
```

The historical command returned **1** before the fixes; the corrected run
returns **0**.

- [Strategy and commands](README.md).
- [Final settings, hashes, tests and repetition summaries](../Results/adam/client-1000/results.json).
- [Raw client latency samples](../Results/adam/client-1000/latencies.json).
- [Query plans](../Results/adam/client-1000/plans.json).
- [10,000-seed results](../Results/adam/client-10000/results.json), [samples](../Results/adam/client-10000/latencies.json), and [plans](../Results/adam/client-10000/plans.json).
- [Protected-access tests](test_protected_access.py).
- [Lifecycle tests](test_lifecycle.py).
- [Concurrent-revocation tests](test_concurrency.py).
- [Unmasked repository-claim tests](test_repository_claims.py).

## Reproduced defects and corrective gates

| Test in `test_repository_claims.py` | Observed result | Required correction |
|---|---|---|
| `test_generated_policy_rejects_another_subject` | Unrelated subject receives the record | Correct the policy generator's subject/object/operation scope; replay generated output |
| `test_generated_policy_rejects_expired_permission` | Expired permission still exposes the record | Define and enforce source/permission validity at access time |
| `test_unique_index_rejects_duplicate_null_parent` | Eight matching roles rather than four | Fix semantic uniqueness with nullable lineage while preserving legitimate multiple paths |
| `test_attribute_wrapper_evaluates_declared_constraint` | `UndefinedColumn`: `attributes` does not exist | Use the actual view contract and consistent relation-type discriminators |

The nullable-key test attempts a duplicate directly; it does not prove that
every recursive path duplicates roles. SQL errors are not successful denials.
These defects are escalated to the authors in the
[manuscript correction roadmap](../../Article/AXES_AMELIORATION_ARTICLE.md).

## Completed 1,000-seed benchmark

One source produces one relation, four roles and 21 permissions. The protected
read/write path also evaluates one profession attribute and an always-true
configured SQL rule. These are synthetic constraints, not clinical replay.

| Clients | Operation | Samples | p50 ms | p95 ms | p99 ms |
|---|---|---:|---:|---:|---:|
| 1 | Source insertion | 1,000 | 3.58 | 12.20 | 26.74 |
| 1 | Permission lookup | 900 | 0.30 | 1.29 | 3.55 |
| 1 | Protected read | 900 | 6.70 | 22.24 | 42.20 |
| 1 | Protected write | 900 | 14.84 | 29.08 | 42.10 |
| 4 | Permission lookup | 3,600 | 0.34 | 0.86 | 1.93 |
| 4 | Protected read | 3,600 | 8.58 | 85.77 | 91.14 |
| 4 | Protected write | 3,600 | 100.09 | 180.82 | 196.51 |
| 1 | Cascade deletion | 100 | 2.29 | 2.61 | 7.69 |

Query percentiles pool three repetitions, each with 300 measured queries per
client after 20 warm-ups. Insertions and deletions are separate single runs.
Latencies include execution and result consumption but not connection setup.
The separately retained wall-clock throughput includes connections/warm-ups;
it is not steady-state maximum throughput.

The second campaign completed with 10,000 seeds and the same test outcomes.
Four-client protected read p50/p95/p99 were 310.86/410.11/517.57 ms; protected
write p50/p95/p99 were 1,011.19/1,600.62/1,901.14 ms. These are measurements
of the experimental adapter, not production-policy performance. Separate runs
do not establish a causal scaling law or production latency target.

## PostgreSQL execution-time benchmark

The SQL-focused campaign uses PostgreSQL's `Execution Time` from `EXPLAIN
(ANALYZE, BUFFERS, TIMING OFF, FORMAT JSON)`, not the client clock. It
includes trigger execution and instrumentation but excludes planning,
network/client handling and commit. Data-modifying statements use `RETURNING`
and the runner rejects plans that return a different number of rows. An
additional focused unit suite tests timing extraction, missing-row handling,
and rejection of mixed timing methods: three passed, exit code 0.

| Seeds | Sessions | Operation | Samples | p50 ms | p95 ms | p99 ms |
|---:|---:|---|---:|---:|---:|---:|
| 1,000 | 1 | Source insertion | 1,000 | 1.17 | 3.79 | 6.71 |
| 1,000 | 1 | Permission lookup | 300 | 0.01 | 0.02 | 0.02 |
| 1,000 | 1 | Protected read | 300 | 4.22 | 4.47 | 4.81 |
| 1,000 | 1 | Protected write | 300 | 12.89 | 13.32 | 13.59 |
| 1,000 | 4 | Protected read | 1,200 | 6.83 | 83.45 | 93.42 |
| 1,000 | 4 | Protected write | 1,200 | 93.34 | 105.77 | 181.23 |
| 10,000 | 1 | Source insertion | 10,000 | 2.27 | 5.71 | 7.20 |
| 10,000 | 1 | Protected read | 300 | 40.76 | 47.54 | 49.92 |
| 10,000 | 4 | Protected read | 1,200 | 308.45 | 399.65 | 513.46 |
| 10,000 | 4 | Protected write | 1,200 | 998.74 | 1,206.48 | 1,511.96 |

Both server-side campaigns reproduced the same 9 passing methods, 3 assertion
failures and 1 SQL error (exit code 1 each). Protected operations use the
experimental adapter, not the defective generated policy.

- [1,000-seed results](../Results/adam/server-1000/results.json) and
  [raw samples](../Results/adam/server-1000/latencies.json).
- [10,000-seed results](../Results/adam/server-10000/results.json) and
  [raw samples](../Results/adam/server-10000/latencies.json).
- [Full table in the manuscript](../../Article/Table/Runtime-Benchmark.tex).

## Boundaries, NoSQL, and acceptance

Read-committed tests show that a new query after committed deletion sees
revocation. An older repeatable-read snapshot retains the old grant until its
transaction ends. Neither proves universal immediate revocation.

At the time of this historical campaign, JWT validation, connection-pool claim
isolation, arbitrary dynamic SQL, all graph depths/cycles/update paths,
clinical-data governance, modern-system baselines, HTTP/k6, deployment,
audit/vault integration, and fresh Rodin proof replay were unverified. The
current-status section above identifies subsequent work. No service-level
latency objective is established.

The MongoDB adaptation is now an executable, limited document prototype:
[adapter](../NoSQL-PoC/mongo_adapter.py), [tests](../NoSQL-PoC/test_mongo_adapter.py), and
[runner](../NoSQL-PoC/run_mongo.py). Eight test methods passed; the 1,000- and 10,000-record
campaigns each recorded 3,000 profiler samples. Results and hashes are retained
in [1,000-record results](../Results/mongodb/1000/results.json) and
[10,000-record results](../Results/mongodb/10000/results.json).

All pooled MongoDB p50/p95/p99 values for the tested reads and updates are
recorded as 0 ms at the profiler's integer-millisecond resolution. This is not
zero latency, and does not justify a numerical speedup. The PostgreSQL and
MongoDB operations use different layouts, instrumentation and authorization
functionality; equivalent durability was not established. The MongoDB prototype has neither recursive
materialization nor graph-wide revocation, snapshot/concurrency tests or a
deployed trusted service. Document storage does not inherit PostgreSQL RLS.

```text
environment:
  docker: AVAILABLE — functional daemon and real PostgreSQL container
  node: AVAILABLE — v24.14.1
  playwright: UNVERIFIED — not applicable; no browser application
  infra-tier: PRIMARY(Docker-based)
  browser-tier: SKIPPED — no rendered application
startup: PASS — exit_code: 0; TCP pg_isready and successful SQL loading
integration: FAIL — exit_code: 1; passed: 9, failed: 3, errors: 1, skipped: 0
e2e: UNVERIFIED — exit_code: n/a; no HTTP/browser/backend integration
overall: FAIL — original implementation claims are contradicted by executable tests
```

After the historical campaign, the four observed defects were corrected and
retested. Before submission, confirm the synthetic case provenance and
applicable ethics requirements, document prior AI tooling, and publish a
versioned reproducible supplement. The revised article is a working revision,
not a submission-ready or production-certified system.
