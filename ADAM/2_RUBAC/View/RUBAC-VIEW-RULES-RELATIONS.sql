CREATE OR REPLACE VIEW view_relations_rules AS
SELECT
     rr.relation_id AS id,
     rr.rule_id,
     rr.params
FROM relations_rules AS rr;