-- security_invoker : sinon la vue tourne avec les droits du propriétaire
-- et saute la RLS des tables dessous (A01-7).
CREATE OR REPLACE VIEW view_relations_rules
    WITH (security_invoker = true) AS
SELECT
     rr.relation_id AS id,
     rr.rule_id,
     rr.params
FROM relations_rules AS rr;