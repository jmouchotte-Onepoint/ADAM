CREATE OR REPLACE VIEW adam.view_roles_rules AS
SELECT
     r.id,
     rel.rule_id,
     rel.params
 FROM adam.roles AS r
     JOIN adam.relations_rules as rel 
     ON r.parent_relation_id = rel.relation_id
     AND is_inheritable is TRUE
 UNION
 SELECT
     r.id,
     rr.rule_id,
     rr.params
 FROM adam.roles AS r
     JOIN adam.roles_rules as rr
     ON r.parent_role_id = rr.role_id
     AND is_inheritable is TRUE
 UNION
 SELECT
     rr.role_id,
     rr.rule_id,
     rr.params
FROM adam.roles_rules AS rr;