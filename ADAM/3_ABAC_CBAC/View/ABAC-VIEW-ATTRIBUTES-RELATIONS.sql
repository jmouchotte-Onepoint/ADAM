-- security_invoker : sinon la vue tourne avec les droits du propriétaire
-- et saute la RLS des tables dessous (A01-7).
CREATE OR REPLACE VIEW view_relations_attributes
    WITH (security_invoker = true) AS
SELECT
     ra.relation_id AS id,
     ra.attribute
FROM relations_attributes AS ra;