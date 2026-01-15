CREATE OR REPLACE VIEW adam.view_relations_attributes AS
SELECT
     ra.relation_id AS id,
     ra.attribute
FROM adam.relations_attributes AS ra;