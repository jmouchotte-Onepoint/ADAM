-- security_invoker : sinon la vue tourne avec les droits du propriétaire
-- et saute la RLS des tables dessous (A01-7).
CREATE OR REPLACE VIEW view_all_access_rules
    WITH (security_invoker = true) AS

SELECT
    'relations' AS relation_type,
    rel.id,
    rel.rule_id,
    rel.params
FROM view_relations_rules AS rel

UNION ALL

SELECT
    'roles' AS relation_type,
    rr.id AS id,
    rr.rule_id,
    rr.params
FROM view_roles_rules AS rr

UNION ALL

SELECT
    'permissions' AS relation_type,
    pr.id AS id,
    pr.rule_id,
    pr.params
FROM view_permissions_rules AS pr;