-- security_invoker : sinon la vue tourne avec les droits du propriétaire
-- et saute la RLS des tables dessous (A01-7).
CREATE OR REPLACE VIEW view_permissions_rules
    WITH (security_invoker = true) AS
SELECT
     p.id,
     rel.rule_id,
     rel.params
 FROM permissions as p
     JOIN relations_rules as rel 
     ON p.parent_relation_id = rel.relation_id
     AND is_inheritable is TRUE
 UNION
 SELECT
     p.id,
     rr.rule_id,
     rr.params
 FROM permissions as p
     JOIN roles_rules as rr
     ON p.parent_role_id = rr.role_id
     AND is_inheritable is TRUE
 UNION
 SELECT
     pr.permission_id,
     pr.rule_id,
     pr.params
FROM permissions_rules AS pr;