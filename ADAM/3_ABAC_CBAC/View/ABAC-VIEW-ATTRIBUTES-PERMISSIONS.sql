CREATE OR REPLACE VIEW adam.view_permissions_attributes AS
SELECT
     p.id,
     rel.attribute
 FROM adam.permissions as p
     JOIN adam.relations_attributes as rel 
     ON p.parent_relation_id = rel.relation_id
     AND is_inheritable is TRUE
 UNION
 SELECT
     p.id,
     ra.attribute
 FROM adam.permissions as p
     JOIN adam.roles_attributes as ra
     ON p.parent_role_id = ra.role_id
     AND is_inheritable is TRUE
 UNION
 SELECT
     pa.permission_id,
     pa.attribute
FROM adam.permissions_attributes AS pa;