CREATE OR REPLACE VIEW adam.view_permissions_rules AS
SELECT
     p.id,
     rel.rule_id,
     rel.params
 FROM adam.permissions as p
     JOIN adam.relations_rules as rel 
     ON p.parent_relation_id = rel.relation_id
     AND is_inheritable is TRUE
 UNION
 SELECT
     p.id,
     rr.rule_id,
     rr.params
 FROM adam.permissions as p
     JOIN adam.roles_rules as rr
     ON p.parent_role_id = rr.role_id
     AND is_inheritable is TRUE
 UNION
 SELECT
     pr.permission_id,
     pr.rule_id,
     pr.params
FROM adam.permissions_rules AS pr;