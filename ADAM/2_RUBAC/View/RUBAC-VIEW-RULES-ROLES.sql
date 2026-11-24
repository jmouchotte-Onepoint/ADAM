-- security_invoker : sinon la vue tourne avec les droits du propriétaire
-- et saute la RLS des tables dessous (A01-7).
CREATE OR REPLACE VIEW view_roles_rules
    WITH (security_invoker = true) AS
SELECT
     r.id,
     rel.rule_id,
     rel.params
 FROM roles AS r
     JOIN relations_rules as rel 
     ON r.parent_relation_id = rel.relation_id
     AND is_inheritable is TRUE
 UNION
 SELECT
     r.id,
     rr.rule_id,
     rr.params
 FROM roles AS r
     JOIN roles_rules as rr
     ON r.parent_role_id = rr.role_id
     AND is_inheritable is TRUE
 UNION
 SELECT
     rr.role_id,
     rr.rule_id,
     rr.params
FROM roles_rules AS rr;