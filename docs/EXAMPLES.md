# Bundled Examples

The `Examples/` folder contains ready-to-run domain samples used to exercise ADAM's model generation and Docker/Liquibase bootstrap. All examples use **anonymized, generic names** — no example is named after a real customer or product.

Each example folder follows the same structure:

```
Examples/<Name>/
├── init-models.yml               # tenants + model (relations/roles/policies/rules)
├── dev-init-relations.yml        # seed relations/roles for dev & test
└── Database/
    ├── docker-entrypoint-initdb.d/     # plain SQL, applied by the postgres container on first boot
    └── adam-entrypoint-dev-test.d/     # Liquibase changelog + SQL, applied under the `dev` context
```

Run any of them with:

```bash
sh example.sh <Name> [target_schema]
```

## Catalog

| Folder | Domain modeled | Notes |
|---|---|---|
| `Northwind` | Generic organization/enterprise access model (collaborators, invitees, roles per department) | Reference example, kept under a generic sample-company name |
| `Fabrikam` | Organization & enterprise membership (organisation/entreprise, member roles) | Simplest example — flat roles, no dynamic rules |
| `Contoso` | Case/file ("dossier") management with a data-controller role and confidentiality-based read policy | Uses a dedicated `contoso` Postgres schema + a dynamic SQL rule |
| `Tailspin` | Variant of `Contoso`'s case-management model | Uses a dedicated `tailspin` Postgres schema |
| `Woodgrove` | Patient/care journey ("parcours") tracking: steps, forms, documents, containers | Most complete example — nested object hierarchy (parcours → etapes → fiches/documents) |

## `init-models.yml` structure (annotated)

```yaml
tenants:
  - id: tenantA                 # tenant identifier used across relations/policies
    name: My_Tenant_A
    description: ...

rules:                          # optional: reusable named SQL conditions
  - id: <uuid>
    sql: select 1 from <schema>.<table> where ... = $param;
    params:
      - param

models:
  type <object_type>:
    relations:                  # who/what can hold this relation on this object type
      - <relation_name>:
        - relations: <other_type>#<sub_relation>   # relation composition (ReBAC)
    roles:                      # named groupings of one or more relations
      - <role_name>:
        - relations: <relation_name>
        policy:                # RLS policy generated for this role
          - name: <policy_name>
            resource: <schema>.<table>
            action: select
            conditions:
              - <column>: <value_or_placeholder>
```

- **`type users: relations: collaborateur / adherent`** is the common building block reused by every example to represent "who belongs to this tenant" (its collaborators and/or external invitees) as a self-attribute of the `users` type.
- **`resource: <schema>.<table>`** in a `policy` block ties a role to a concrete Postgres table for Row-Level Security.
- **Relation composition** (`relations: users#collaborateur`) lets a role require membership through another type's relation, enabling multi-level ReBAC chains (e.g. a "reader" role on a `dossier` granted through `proprietaire`/`gestionnaire` relations defined on the parent tenant object). The condition-check function resolves this either against the target object or as a self-referencing fact on the user itself (`user: "users:X", relation: "collaborateur", object: "users:X"`) — the pattern used by `Contoso`, `Tailspin` and `Woodgrove` (`users#doctor`).

## `dev-init-relations.yml` structure

```yaml
<tenant_id>:
  - user: "<user_type>:<user_id>"
    relation: "<relation_name>"
    object: "<object_type>:<object_id>"
    type: "roles"        # optional — defaults to "relations" if omitted
```

Each entry is turned into an `INSERT INTO relations (...)` or `INSERT INTO roles (...)` statement (see `init_data_dev_test.py`) written to `ADAM/5_DEV_TEST/ADAM-0001-ADD-RELATIONS.sql`, which the example's own Liquibase changelog applies under the `dev` context.

## Known limitations discovered during verification

While validating the renamed examples end to end (see the project's `docs/README.md` quick start), one pre-existing issue remains, unrelated to the anonymization pass:

1. **`Northwind`**: seeding `ADAM-0001-ADD-RELATIONS` fails with `No authorization model found for user_type=client, relation=dataController, object_type=...`. The dev/test seed data references a relation named `dataController`, while the model actually defines a more specific `collaborateurDataController` relation (rolled up into the `roleDataController` role) — the seed data was not updated to match the current model.

`Fabrikam`, `Contoso`, `Tailspin` and `Woodgrove` were verified to run cleanly end to end (Liquibase `update` succeeds with all dev/test relations inserted). `Contoso` and `Tailspin` originally failed with `Condition relationnelle non satisfaite` on the `dataController` relation — this was traced to a mismatch between the `client#collaborateur` relation-composition prefix and the underlying `collaborateur`/`adherent` facts (recorded as `users:X` holding a relation on a `client:X` pseudo-object, rather than as the self-referencing `users:X → users:X` fact the condition-check function expects, mirroring `Woodgrove`'s working `users#doctor` pattern). The fix renamed the shared `type client:` block to `type users:` and switched the composition prefixes to `users#collaborateur` / `users#adherent`, with the seed data updated to record `collaborateur`/`adherent` as self-referencing facts on the `users` type.

