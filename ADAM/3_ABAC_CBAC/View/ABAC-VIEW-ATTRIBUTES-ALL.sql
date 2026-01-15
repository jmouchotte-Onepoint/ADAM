CREATE OR REPLACE VIEW adam.view_all_access_attributes AS

SELECT
    'relations' AS relation_type,
    rel.id,
    rel.attribute
FROM adam.view_relations_attributes AS rel

UNION ALL

SELECT
    'roles' AS relation_type,
    ra.id,
    ra.attribute
FROM adam.view_roles_attributes AS ra

UNION ALL

SELECT
    'permissions' AS relation_type,
    pa.id,
    pa.attribute
FROM adam.view_permissions_attributes AS pa;