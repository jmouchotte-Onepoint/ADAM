CREATE OR REPLACE VIEW adam.view_roles_attributes AS
SELECT
     r.id,
     rel.attribute
 FROM adam.roles AS r
     JOIN adam.relations_attributes as rel 
     ON r.parent_relation_id = rel.relation_id
     AND is_inheritable is TRUE
 UNION
 SELECT
     r.id,
     ra.attribute
 FROM adam.roles AS r
     JOIN adam.roles_attributes as ra
     ON r.parent_role_id = ra.role_id
     AND is_inheritable is TRUE
 UNION
 SELECT
     ra.role_id,
     ra.attribute
FROM adam.roles_attributes AS ra;