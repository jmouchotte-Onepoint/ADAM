# ADAM — Authorization Data & Access Model

ADAM is a PostgreSQL-based authorization engine that combines **ReBAC** (Relationship-Based Access Control), **RBAC** (Role-Based Access Control), **RUBAC** (Rule-Based Access Control) and **ABAC/CBAC** (Attribute/Context-Based Access Control) into a single, tenant-aware permission model.

Given a YAML description of your domain (object types, relations, roles, rules, tenants), ADAM generates the SQL needed to:

- Create the authorization schema (relations, roles, permissions, model, tenants, ...).
- Populate Row-Level-Security (RLS) policies and dynamic SQL rules.
- Seed relations/roles for local development and testing.

This document explains how the project is organized, how to install it, and how to run it end to end. See [EXAMPLES.md](EXAMPLES.md) for a walkthrough of the bundled example domains.

## Prerequisites

- **Python 3.10+**
- **[uv](https://docs.astral.sh/uv/)** for dependency management and running scripts
- **Docker** and **Docker Compose** (to run PostgreSQL + Liquibase locally)

Install the Python dependencies:

```bash
uv sync
```

## Project layout

```
ADAM/                   # Liquibase changelogs applied in layers (see below)
Docker/                 # Base docker-entrypoint init scripts / postgres config
Examples/               # Sample domains you can bootstrap out of the box
Resources/              # Shared Python helpers (YAML loading, SQL writers, utils)
main.py                 # CLI entry point that turns YAML into SQL
init_archi_rls_sql.py   # Generates model/roles/policy/RLS/tenants/rules SQL
init_data_dev_test.py   # Generates dev/test relation & role seed SQL
example.sh              # One-shot script to bootstrap a given example via Docker
docker-compose.yml       # postgres + liquibase services
```

### The layered ADAM changelog (`ADAM/changelog.xml`)

Liquibase applies the following changelogs in order, each layer building on the previous one:

| Layer | Folder | Purpose |
|---|---|---|
| 0 | `0_INIT` | Base schema creation, tenants table, initial DB users |
| 1 | `1_REBAC_RBAC` | Core relationship model, relations/roles/permissions tables, functions, triggers, policies |
| 2 | `2_RUBAC` | Rule-based access control: dynamic SQL rules attached to relations/roles/permissions |
| 3 | `3_ABAC_CBAC` | Attribute/context-based conditions layered on top of RBAC/RUBAC |
| 4 | `4_INSERT` | Generated SQL from `main.py --models` (your domain's model, policies, RLS, tenants, rules) |
| 5 | `5_DEV_TEST` | Example-specific dev/test data (schema init + seeded relations), only applied with the `dev` context |

## Quick start: run a bundled example

`example.sh` wires everything together: it copies an example's database seed files into place, generates the ADAM SQL from that example's YAML, and starts PostgreSQL + Liquibase via Docker Compose.

```bash
sh example.sh <ExampleName> [target_schema]
```

- `<ExampleName>` — a folder name under `Examples/` (e.g. `Fabrikam`, `Contoso`, `Tailspin`, `Woodgrove`, `Northwind`).
- `[target_schema]` — optional Postgres schema to use as the default `search_path` (defaults to `adam`).

Example:

```bash
sh example.sh Woodgrove
```

This will:
1. Tear down any previous stack (`docker compose down -v`).
2. Copy `Examples/Woodgrove/Database/docker-entrypoint-initdb.d/*` and `Examples/Woodgrove/Database/adam-entrypoint-dev-test.d/*` into the local Docker init folders.
3. Run `main.py --models` and `main.py --relations` against that example's YAML files.
4. Start `docker compose up -d` (PostgreSQL + Liquibase, applying all changelog layers including `5_DEV_TEST`).

Check the migration result:

```bash
docker compose logs liquibase
```

## `main.py` CLI reference

`main.py` reads YAML configuration and writes ADAM-ready SQL files. It never talks to the database directly — the resulting `.sql` files are meant to be picked up by the Liquibase changelogs above.

### `--models <path/to/init-models.yml>`

Generates the model definition, RBAC/RUBAC policies, RLS policies, tenants and dynamic rules:

```bash
uv run ./main.py --models ./Examples/Woodgrove/init-models.yml
```

Outputs:
- `./ADAM/4_INSERT/INSERT-MODEL-POLICY.sql`
- `./ADAM/4_INSERT/INSERT-MODEL-POLICY-RULES.sql`
- `./ADAM/4_INSERT/INSERT-RLS-POLICY.sql`
- `./ADAM/4_INSERT/INSERT-TENANTS.sql`
- `./ADAM/4_INSERT/INSERT-DYNAMIC-RULES.sql`

### `--relations <path/to/dev-init-relations.yml>`

Generates dev/test seed data (relations and roles) for the ReBAC model:

```bash
uv run ./main.py --relations ./Examples/Woodgrove/dev-init-relations.yml
```

Output:
- `./ADAM/5_DEV_TEST/ADAM-0001-ADD-RELATIONS.sql`

> This generated file must be referenced from the example's own `changelog.xml` (under `Database/adam-entrypoint-dev-test.d/`) so Liquibase picks it up with the `dev` context.

## YAML configuration reference

Each example provides two YAML files:

- **`init-models.yml`** — defines `tenants`, `models` (object types, their `relations`/`roles`/`permissions` and attached `policy`/`rules`), and optionally top-level `rules` (named, parameterized SQL conditions reusable across policies).
- **`dev-init-relations.yml`** — defines, per tenant, a list of `user` / `relation` / `object` triples (optionally `type: roles`) used to seed the ReBAC graph for local development and manual testing.

See [EXAMPLES.md](EXAMPLES.md) for an annotated walkthrough of these files.
