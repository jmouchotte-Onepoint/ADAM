-- security_invoker : sinon la vue tourne avec les droits du propriétaire
-- et saute la RLS des tables dessous (A01-7).
CREATE OR REPLACE VIEW view_roles_attributes
    WITH (security_invoker = true) AS
SELECT
     r.id,
     rel.attribute
 FROM roles AS r
     JOIN relations_attributes as rel 
     ON r.parent_relation_id = rel.relation_id
     AND is_inheritable is TRUE
 UNION
 SELECT
     r.id,
     ra.attribute
 FROM roles AS r
     JOIN roles_attributes as ra
     ON r.parent_role_id = ra.role_id
     AND is_inheritable is TRUE
 UNION
 SELECT
     ra.role_id,
     ra.attribute
FROM roles_attributes AS ra;