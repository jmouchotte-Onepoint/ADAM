CREATE OR REPLACE VIEW adam.view_relations_rules AS
SELECT
     rr.relation_id AS id,
     rr.rule_id,
     rr.params
FROM adam.relations_rules AS rr;