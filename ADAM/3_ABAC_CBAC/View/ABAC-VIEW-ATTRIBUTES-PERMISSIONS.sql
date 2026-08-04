CREATE OR REPLACE VIEW view_permissions_attributes AS
SELECT
     p.id,
     rel.attribute
 FROM permissions as p
     JOIN relations_attributes as rel 
     ON p.parent_relation_id = rel.relation_id
     AND is_inheritable is TRUE
 UNION
 SELECT
     p.id,
     ra.attribute
 FROM permissions as p
     JOIN roles_attributes as ra
     ON p.parent_role_id = ra.role_id
     AND is_inheritable is TRUE
 UNION
 SELECT
     pa.permission_id,
     pa.attribute
FROM permissions_attributes AS pa;