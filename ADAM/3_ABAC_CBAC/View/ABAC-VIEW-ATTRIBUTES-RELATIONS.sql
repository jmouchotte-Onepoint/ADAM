CREATE OR REPLACE VIEW view_relations_attributes AS
SELECT
     ra.relation_id AS id,
     ra.attribute
FROM relations_attributes AS ra;